"""P-A2T Stage-1 A0 flight PRE-FLIGHT check -- ZERO model contact.

Verifies, before any core contact:
  1. the frozen 400-item discovery split resolves through the shipped adapter,
     all media present, and its receipt's split identity hash is the one the
     binding table names;
  2. exactly ONE audio2tool probe receipt declares split_role=discovery (a
     second one would silently widen the split ``load_split`` returns);
  3. the exposure row SAEA-BASE-a2t-a0-400 exists exactly once, reads
     consumed=no, carries the FULL 64-hex split identity hash verbatim, names
     exactly one known carrier lock key, and registers budgets >= the plan's;
  4. the ExecutionPlan validates as baseline-reproduction / discovery;
  5. the payload binding builds (media confinement, sample-rate probe);
  6. the ``-np 1`` context delta is present and the registry prefill fits.
Nothing here opens a socket, spawns a server, or reads a model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _EXPOSURE_CARRIER_COLUMN,
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    model_lock_key,
    protocol_hash as compute_protocol_hash,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    audio2tool_receipts,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.runner import RAILS_ARMS  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402
from flight_plan import (  # noqa: E402
    PLANNED_GPU_HOURS,
    PLANNED_MODEL_CALLS,
    PLANNED_SPEECH_AUDIO_SECONDS,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/pa2t-a0-flight.json").read_text(encoding="utf-8")
)
BINDING = json.loads(
    (REPO / "configs/probes/g0-binding/pa2t-binding.json").read_text(encoding="utf-8")
)


def main() -> int:
    problems: list[str] = []
    module_root = Path(__import__("speech_aware_evidence_acquisition").__file__).parent
    print(f"repo module root: {module_root}")
    if module_root != REPO / "src" / "speech_aware_evidence_acquisition":
        problems.append(f"module resolved outside this checkout: {module_root}")

    pyc = sorted((REPO / "src").rglob("*.pyc"))
    print(f"__pycache__ .pyc files under src/: {len(pyc)}")
    if pyc:
        problems.append(f"{len(pyc)} .pyc under src/ -- the D3 gate refuses bytecode; first {pyc[:3]}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    print(f"carrier_root (asset_dir audio2tool): {carrier_root}")

    # ---- 1/2. split identity ------------------------------------------------
    receipts = audio2tool_receipts(REPO)
    discovery_receipts = {
        name: payload
        for name, payload in receipts.items()
        if payload.get("split_role") == "discovery"
    }
    print(f"audio2tool receipts declaring split_role=discovery: {sorted(discovery_receipts)}")
    if len(discovery_receipts) != 1:
        problems.append(
            f"expected exactly 1 discovery receipt, found {sorted(discovery_receipts)}"
        )
    receipt_payload = next(iter(discovery_receipts.values()))
    split_hash = str(receipt_payload["split_identity_hash"])
    print(f"split_identity_hash (from the receipt): {split_hash}")
    for source, expected in (
        ("pa2t-a0-flight.json", FLIGHT_CFG["split_identity"]["split_identity_hash"]),
        ("pa2t-binding.json", BINDING["split_identity"]["split_identity_hash"]),
        ("pa2t-a0-flight.json execution_plan", FLIGHT_CFG["execution_plan"]["split_identity_hash"]),
    ):
        if expected != split_hash:
            problems.append(f"{source} split hash {expected!r} != receipt {split_hash!r}")
    if len(split_hash) != 64:
        problems.append(f"split identity hash is not 64-hex: {split_hash!r}")

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving discovery split (sha256 of every media file -- slow, model-free)")
    samples = adapter.load_split("discovery")
    print(f"discovery split resolved: {len(samples)} samples")
    if len(samples) != int(FLIGHT_CFG["split_identity"]["n_items"]):
        problems.append(
            f"split resolved {len(samples)} samples, flight config declares "
            f"{FLIGHT_CFG['split_identity']['n_items']}"
        )
    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing:
        problems.append(f"{len(missing)} sample media missing: {missing[:5]}")
    total_audio = sum(s.audio_seconds for s in samples)
    max_audio = max(s.audio_seconds for s in samples)
    print(f"media resolved: {len(samples) - len(missing)}/{len(samples)}")
    print(f"total audio seconds: {total_audio:.2f} (max item {max_audio:.2f})")
    if total_audio > PLANNED_SPEECH_AUDIO_SECONDS:
        problems.append(
            f"one full pass needs {total_audio:.2f} audio seconds but the plan claims only "
            f"{PLANNED_SPEECH_AUDIO_SECONDS}"
        )

    # ---- arms ---------------------------------------------------------------
    arms = tuple(FLIGHT_CFG["arms"])
    print(f"arms: {arms} (rails arms: {RAILS_ARMS})")
    for arm in arms:
        if arm not in RAILS_ARMS:
            problems.append(f"arm {arm!r} is not a rails arm")
    if arms != ("zero-supply",):
        problems.append(f"A0 flies exactly ('zero-supply',), config declares {arms}")

    # ---- 6. context sizing --------------------------------------------------
    values = build_values(REPO)
    argv = [str(t) for t in values["server_args"]]
    print(f"server_args (after the -np delta): {argv}")
    ctx = int(argv[argv.index("-c") + 1])
    npar = int(argv[argv.index("-np") + 1])
    per_slot = ctx // npar
    schemas = render_tool_schemas(lock, root)
    instruction_chars = len(
        "You control tools. Available tools:\n" + schemas + "\n\n"
        'Respond with ONLY a JSON array of tool calls, e.g. [{"name": "x", "arguments": {}}].'
    )
    est_tokens = instruction_chars // 4
    print(f"per-slot context: {ctx}/{npar} = {per_slot} tokens")
    print(f"system instruction: {instruction_chars} chars, est {est_tokens} tokens")
    if npar != 1:
        problems.append(f"-np is {npar}, delta 4 did not apply")
    if per_slot < est_tokens * 2:
        problems.append(
            f"per-slot context {per_slot} leaves under 2x headroom over the ~{est_tokens}-token "
            "registry prefill (plus audio, plus 1024 output tokens)"
        )
    max_out = int(values["decoding_params"].get("max_tokens", 0))
    print(f"max_tokens: {max_out}; worst-case sequence ~{est_tokens + 500 + max_out} tokens")

    # ---- 3. exposure ledger row ---------------------------------------------
    rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
    matched = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == RUN_ID]
    print(f"exposure rows matching run id {RUN_ID!r}: {len(matched)}")
    if len(matched) != 1:
        problems.append(f"expected exactly 1 exposure row, found {len(matched)}")
    else:
        row = matched[0]
        for col in (
            "execution profile",
            "split role",
            "split identity hash",
            "consumed",
            "calls",
            "speech audio seconds",
            "gpu hours",
        ):
            print(f"  ledger[{col!r}] = {row.get(col)!r}")
        print(f"  ledger[{_EXPOSURE_CARRIER_COLUMN!r}] = {row.get(_EXPOSURE_CARRIER_COLUMN)!r}")
        if row.get("split identity hash") != split_hash:
            problems.append(
                "LEDGER CELL MISMATCH: 'split identity hash' cell is "
                f"{row.get('split identity hash')!r} but the plan carries {split_hash!r}; "
                "FrozenCoreGate compares these verbatim -- the gate WILL refuse."
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        if row.get("execution profile") != FLIGHT_CFG["execution_plan"]["execution_profile"]:
            problems.append("exposure row execution profile disagrees with the plan")
        if row.get("split role") != FLIGHT_CFG["execution_plan"]["split_role"]:
            problems.append("exposure row split role disagrees with the plan")
        for col, planned, parse in (
            ("calls", PLANNED_MODEL_CALLS, int),
            ("speech audio seconds", PLANNED_SPEECH_AUDIO_SECONDS, int),
            ("gpu hours", PLANNED_GPU_HOURS, float),
        ):
            try:
                registered = parse(str(row.get(col)))
            except ValueError:
                problems.append(f"ledger column {col!r} is not a number: {row.get(col)!r}")
                continue
            if registered < planned:
                problems.append(f"ledger {col}={registered} < planned {planned}")

    # ---- 4. plan ------------------------------------------------------------
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"server_env: {values['server_env']}")
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=FLIGHT_CFG["execution_plan"]["execution_profile"],
        carrier_lock_key=FLIGHT_CFG["execution_plan"]["carrier_lock_key"],
        split_role=FLIGHT_CFG["execution_plan"]["split_role"],
        split_identity_hash=split_hash,
        planned_model_calls=PLANNED_MODEL_CALLS,
        planned_gpu_hours=PLANNED_GPU_HOURS,
        planned_speech_audio_seconds=PLANNED_SPEECH_AUDIO_SECONDS,
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(
        f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role} "
        f"calls={plan.planned_model_calls} audio_s={plan.planned_speech_audio_seconds} "
        f"gpu_h={plan.planned_gpu_hours}"
    )

    # ---- 5. payload binding -------------------------------------------------
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=carrier_root,
    )
    rates = {binding.sample_facts[s.sample_id][1] for s in samples}
    print(f"payload binding built: {len(binding.allowed_sample_ids)} ids, sample rates {sorted(rates)}")

    # ---- 7. FULL GATE DRY-RUN ----------------------------------------------
    # assert_model_touch_allowed is pure authorization: it validates the plan,
    # cross-checks the exposure row, resolves the carrier against the umbrella
    # lock and verifies both receipts. It contacts no model and opens no
    # socket, so running it here turns every gate refusal into a pre-flight
    # failure instead of a refusal after the server is already up.
    # full_hash=False fast-paths the 30 GB GGUF verification; the real flight
    # pays for one genuine full SHA-256 pass per session (the gate's own
    # default, which FrozenCoreAdapter never overrides).
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path("/home/chao"),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
    )
    try:
        lock_sha = gate.assert_model_touch_allowed(plan, full_hash=False)
        print(f"GATE DRY-RUN: model touch AUTHORIZED (umbrella lock sha256 {lock_sha})")
    except Exception as error:  # noqa: BLE001
        problems.append(f"GATE DRY-RUN REFUSED -> {type(error).__name__}: {error}")

    print()
    if problems:
        print(f"PRE-FLIGHT PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("PRE-FLIGHT CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
