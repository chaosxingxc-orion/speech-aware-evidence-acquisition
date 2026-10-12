#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The cell ROLL-AA read (board route F2, the Stage-3 within-flight A/A null; decision 58 by
# script). MODEL-FREE: zero model / tokenizer / encoder / server contacts; scorer contacts only on
# derived COPIES (two: one per sample index). Registered as
# SAEA-SLURP-STAGE3-ROLL-AA-READ-V1, a model-free-check row.
#
# It is NOT an admission read and never calls scripts/analysis/plan_cell_read.py: an A/A null's two
# sides are two samples of the SAME Solver visit of the SAME flight, so the cell is its own control
# and there is no comparator to gate against.
#
# Stage 1-3: scripts/analysis/stage3_rollout_score.py render / score / pairs on copies, exactly as
#            cell ROLL-1's own read runs (sample count auto-detected; asserted here as 2).
# Stage 4:   the paired-delta null of docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1/
#            analysis-recipe-v1.json -- per row delta = sample1 - sample0 for official SLU-F1 and
#            intent, the pooled micro delta with CI95 by paired row bootstrap (10,000 draws, seed
#            20260915), the byte-identical / intent-flip / entity-set-flip shares, the per-stratum
#            table and the commit-effect count. Output: h_within and h_within_intent.
#
# No utterance text, gold label, transcript or model output is printed or persisted by stage 4:
# null.json and per_row_null.json carry ids, stratum names, sample indices, scores, flags and
# hashes only.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
RUN=${RUN:-SAEA-SLURP-STAGE3-ROLL-AA-V1}
ATTEMPT=${ATTEMPT:-attempt-slurp-native-stage3-roll-aa-v1-generation}
ROSTER=${ROSTER:-docs/receipts/rosters/slurp-stage3-roll-aa-r01c-200-v1.json}
SCORER=${SCORER:-slurp-slu-official-projected-v3-train}
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-AA-READ-V1
mkdir -p "$ROOT" && cp "$MAIN/scripts/analysis/stage3_rollout_score.py" "$ROOT/stage3_rollout_score.py" || exit 1
cd "$ROOT" || exit 1
echo "driver sha256 $(sha256sum stage3_rollout_score.py | cut -c1-16)"
for stage in render score pairs; do
  echo "== stage $stage $(date -u +%T)"
  $PY -B stage3_rollout_score.py --stage $stage \
    --run "$RUN" --attempt "$ATTEMPT" --roster "$ROSTER" --samples 2 \
    --scorer-id "$SCORER" --repo-root "$MAIN" --analysis-root "$ROOT" \
    > "$ROOT/stage-$stage.log" 2>&1 || { echo "STAGE $stage FAILED"; tail -5 "$ROOT/stage-$stage.log" | cut -c1-300; exit 2; }
done
echo "== stage null $(date -u +%T)"
RUN="$RUN" ATTEMPT="$ATTEMPT" ROOT="$ROOT" MAIN="$MAIN" $PY -B - <<'PY' > "$ROOT/stage-null.log" 2>&1 || { echo "STAGE null FAILED"; tail -10 "$ROOT/stage-null.log" | cut -c1-300; exit 3; }
import json, os, random, statistics, sys
from pathlib import Path

ROOT = Path(os.environ["ROOT"])
MAIN = Path(os.environ["MAIN"])
sys.path.insert(0, str(MAIN / "src"))
sys.path.insert(0, str(ROOT))
import stage3_rollout_score as s3  # the COPY beside this read, never the repository file
from speech_aware_evidence_acquisition.data.lock import data_root as resolve_data_root

BOOTSTRAP_DRAWS, SEED = 10000, 20260915
directory = s3.run_dir(resolve_data_root(), os.environ["RUN"], os.environ["ATTEMPT"])

# ---- the two samples' raw-response digests, straight out of the sealed custody -------------
# solver_group.samples[i].contacts[-1].response_text_sha256 is the byte digest of the raw model
# response; no response TEXT is read, printed or persisted anywhere by this stage.
digests, seeds, temps = {}, {}, {}
for row in s3.iter_jsonl(directory / ("%s.outputs.jsonl" % os.environ["RUN"])):
    group = row.get("solver_group")
    if not isinstance(group, dict):
        continue
    sid = row["sample_id"]
    digests[sid] = [r["contacts"][-1]["response_text_sha256"] for r in group["samples"]]
    seeds[sid] = [r["seed"] for r in group["samples"]]
    temps[sid] = [r["temperature"] for r in group["samples"]]

per_row = json.loads((ROOT / "per_row.json").read_text(encoding="utf-8"))
rows = per_row["rows"] if isinstance(per_row, dict) and "rows" in per_row else per_row


def entity_key(answer):
    if not isinstance(answer, dict):
        return None
    return tuple(sorted((str(e.get("type", "")).strip().lower(),
                         " ".join(str(e.get("filler", "")).split()).lower())
                        for e in (answer.get("entities") or [])))


parsed = {}
for row in s3.iter_jsonl(directory / ("%s.outputs.jsonl" % os.environ["RUN"])):
    group = row.get("solver_group")
    if isinstance(group, dict):
        parsed[row["sample_id"]] = [r.get("parsed_answer") for r in group["samples"]]

records = []
for row in rows:
    sid = row["sample_id"]
    samples = {int(s["sample_index"]): s for s in row["samples"]}
    a, b = samples[0], samples[1]
    left, right = (parsed.get(sid) or [None, None])[0], (parsed.get(sid) or [None, None])[1]
    records.append({
        "sample_id": sid,
        "stratum": row.get("stratum"),
        "slu_0": float(a["slu_f1_f1"]), "slu_1": float(b["slu_f1_f1"]),
        "intent_0": bool(a["scenario_action_exact"]), "intent_1": bool(b["scenario_action_exact"]),
        "delta_slu": float(b["slu_f1_f1"]) - float(a["slu_f1_f1"]),
        "delta_intent": int(bool(b["scenario_action_exact"])) - int(bool(a["scenario_action_exact"])),
        "byte_identical": len(set(digests.get(sid, []))) == 1 if sid in digests else None,
        "intent_flip": None if left is None or right is None else (
            (left.get("scenario"), left.get("action")) != (right.get("scenario"), right.get("action"))),
        "entity_set_flip": None if left is None or right is None else (
            entity_key(left) != entity_key(right)),
        "seeds": seeds.get(sid), "temperatures": temps.get(sid),
    })

n = len(records)
if n == 0:
    raise SystemExit("no rows")


def half_width(values):
    rng = random.Random(SEED)
    means = []
    for _ in range(BOOTSTRAP_DRAWS):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo, hi = means[int(0.025 * BOOTSTRAP_DRAWS)], means[int(0.975 * BOOTSTRAP_DRAWS) - 1]
    return lo, hi, (hi - lo) / 2


def block(values, scale):
    vals = [v * scale for v in values]
    lo, hi, h = half_width(vals)
    return {"mean": sum(vals) / n, "sd": statistics.pstdev(vals) if n > 1 else 0.0,
            "ci95": [lo, hi], "ci95_half_width": h, "n": n}


def share(key):
    known = [r[key] for r in records if r[key] is not None]
    return {"share": (sum(1 for v in known if v) / len(known)) if known else None,
            "count": sum(1 for v in known if v), "denominator": len(known),
            "unknown": n - len(known)}


strata = {}
for r in records:
    strata.setdefault(r["stratum"], []).append(r)

null = {
    "schema": "saea-stage3-roll-aa-within-flight-null-v1",
    "recipe_id": "slurp-stage3-roll-aa-within-flight-null-v1",
    "run_id": os.environ["RUN"], "attempt_id": os.environ["ATTEMPT"], "rows": n,
    "resampling": {"draws": BOOTSTRAP_DRAWS, "seed": SEED, "unit": "row (paired)"},
    "h_within": block([r["delta_slu"] for r in records], 100.0),
    "h_within_intent": block([r["delta_intent"] for r in records], 100.0),
    "byte_identical_output": share("byte_identical"),
    "intent_flip": share("intent_flip"),
    "entity_set_flip": share("entity_set_flip"),
    "per_stratum": {
        k: {"rows": len(v),
            "mean_delta_slu_pp": 100.0 * sum(r["delta_slu"] for r in v) / len(v),
            "mean_delta_intent_pp": 100.0 * sum(r["delta_intent"] for r in v) / len(v)}
        for k, v in sorted(strata.items())
    },
    "custody_check": {
        "rows_with_two_samples": sum(1 for r in records if r["seeds"] and len(r["seeds"]) == 2),
        "distinct_seed_sets": sorted({tuple(r["seeds"]) for r in records if r["seeds"]}),
        "distinct_temperature_sets": sorted({tuple(r["temperatures"]) for r in records if r["temperatures"]}),
    },
    "reported_beside": {
        "note": "CROSS-FLIGHT own-null half-widths, context only, never a comparator and never a gate.",
        "train_fold_a": {"h_slu": 1.2485, "h_intent": 0.9943, "n": 1080},
        "dev_2000_added": {"h_slu": 1.2525, "h_intent": 1.1520, "n": 2000},
    },
    "claim_boundary": (
        "DESCRIPTIVE. h_within is the within-flight paired measurement floor at n = 200, on the "
        "nine scenario strata of this roster, at samples 2, on the np4 x 24,576 SLURP geometry. "
        "No transfer, superiority, generalisation or confirmatory claim."
    ),
}
(ROOT / "null.json").write_text(json.dumps(null, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(ROOT / "per_row_null.json").write_text(
    json.dumps({"schema": "saea-stage3-roll-aa-per-row-null-v1", "rows": records},
               indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in null.items() if k != "per_stratum"}, indent=2, sort_keys=True))
PY
echo "ROLL-AA read done $(date -u +%T)"; tail -40 "$ROOT/stage-null.log"; ls "$ROOT"
