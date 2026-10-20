#!/usr/bin/env python3
"""ASRBIAS instrument: contextually biased Qwen3-ASR transcription of the TRAIN Fold B roster on CPU.

Owner direction 2026-10-19 (proper-noun-enhanced ASR decoding). Package:
docs/readiness/2026-10-19-slurp-asrbias-foldb-transcription-v1/. Sibling of foldb_transcription.py (the V0 instrument,
ASR339); it reuses that module's parsing, hashing, roster and scoring. It is an INSTRUMENT: it measures how far a
context (type vocabulary, intent-scoped value lexicon, first-token logit bias, n-best union) moves the tool's
transcripts. It never answers, never reaches the core (port 8080) and is never a delivery step.

Variants (configs/asr_bias/variant-<id>.json, registry VARIANT_IDS):
    v0 none | v1 slot-type vocabulary | v2-n30 / v2-n100 intent-scoped value lexicon | v3-* = v2 + logit_bias on the
    first token of each lexicon value | v4-* = 5 sampled decodes, transcripts concatenated for containment.
The context is rendered as the SYSTEM message (the Qwen3-ASR chat template is plain ChatML: a system turn, then the
user turn carrying only the input_audio part), the same placement as the model card.

Subcommands:
    build-lexicon --out FILE      TRAIN type-value counts excluding Fold A and Fold B utterances + the committed
                                  intent per Fold B row (the v3.0 lock column, the system's own output, not gold)
    transcribe --model-id M --variant V --out-root DIR --lexicon FILE [--rows N] [--smoke | --full] [--port P]
    score ...                     delegates unchanged to foldb_transcription.py score
Text discipline: no utterance, transcript, reference, lexicon value or gold value is printed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import sys
import time
import urllib.request
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CONFIG_DIR = REPO / "configs" / "asr_bias"
PACKAGE_ID = "slurp-asrbias-foldb-transcription-v1"
LEDGER_ROW_ID = "SAEA-SLURP-ASRBIAS-FOLD-B-V1"
SCHEMA_ROW = "saea-asrbias-transcript-row-v1"
SCHEMA_CATALOG = "saea-asrbias-transcript-catalog-v1"
SCHEMA_LEXICON = "saea-asrbias-lexicon-v1"
SCHEMA_VARIANT = "saea-asrbias-variant-v1"
VARIANT_IDS = ("v0", "v1", "v2-n30", "v2-n100", "v3-n30", "v3-n100", "v4-none", "v4-n100")
CONTEXT_KINDS = ("none", "type-vocabulary", "intent-lexicon")
SMOKE_MAX_ROWS = 4
CONTEXT_TOKEN_BUDGET = 768  # hard cap on the rendered context text, counted with the model tokenizer at run time
APPROX_CHARS_PER_TOKEN = 3.0  # conservative offline estimator (real text runs 3.5-4.5 chars per token)
TOP_PER_TYPE = 100
MIN_TYPE_PRIOR = 0.02
BIAS_STOP_WORDS = frozenset("a an the of to in on at for and or my me i is it this that".split())
BIAS_MIN_WORD_CHARS = 3
MAX_BIAS_TOKENS = 400
SEP = " <SEP> "
HEADER_TYPES = "The audio is a short spoken command to a voice assistant. Slot types that may occur in it:"
HEADER_TERMS = "The audio is a short spoken command to a voice assistant. Words and names that may occur in it: "
BASE_DECODING = {"schema": "saea-asrbias-decode-v1", "max_tokens": 256, "endpoint": "/v1/chat/completions",
                 "audio_part": "input_audio", "context_placement": "system-message", "device": "cpu",
                 "session_slots": 1}


class InstrumentError(RuntimeError):
    pass


def _imp(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


BASE = _imp(HERE / "foldb_transcription.py", "asr339_base_for_asrbias")
sha256_bytes, sha256_file, canonical_json = BASE.sha256_bytes, BASE.sha256_file, BASE.canonical_json


# ---------------------------------------------------------------------------------------------- registry


def load_variant(variant_id: str, config_dir: Path = CONFIG_DIR) -> dict:
    if variant_id not in VARIANT_IDS:
        raise InstrumentError(f"variant {variant_id!r} is not in the registry {VARIANT_IDS}")
    path = Path(config_dir) / f"variant-{variant_id}.json"
    raw = path.read_bytes()
    doc = json.loads(raw)
    if doc.get("schema") != SCHEMA_VARIANT or doc.get("variant_id") != variant_id:
        raise InstrumentError(f"{path.name}: schema or variant_id does not match the registry id")
    if doc["context"] not in CONTEXT_KINDS:
        raise InstrumentError(f"{path.name}: context {doc['context']!r} does not resolve")
    if doc["context"] == "intent-lexicon" and not doc.get("lexicon_n"):
        raise InstrumentError(f"{path.name}: intent-lexicon needs lexicon_n")
    if doc["first_token_bias"] and doc["context"] != "intent-lexicon":
        raise InstrumentError(f"{path.name}: a first-token bias needs the intent lexicon")
    dec = doc["decode"]
    if dec["samples"] > 1 and (dec["temperature"] <= 0 or len(dec["seeds"]) != dec["samples"]):
        raise InstrumentError(f"{path.name}: sampled decoding needs temperature > 0 and one seed per sample")
    doc["_sha256"] = sha256_bytes(raw)
    return doc


def type_descriptions(config_dir: Path = CONFIG_DIR) -> dict:
    return json.loads((Path(config_dir) / "slot-type-descriptions-v1.json").read_text(encoding="utf-8"))["types"]


# ---------------------------------------------------------------------------------------------- lexicon


def build_lexicon(records, excluded_utterances, top_per_type: int = TOP_PER_TYPE) -> dict:
    """records: iterable of (utterance_id, intent, [(slot_type, filler), ...]), one per recording.

    Only utterances outside ``excluded_utterances`` (Fold A and Fold B utterance ids) contribute, and each utterance
    contributes once. By construction a Fold B row's own utterance never feeds the lexicon.
    Returns {"type_values": {type: [value, ...] by descending count then alphabetical, top N},
             "intent_type_prior": {intent: {type: P(type present | intent)}}, "n_utterances": int}."""
    excluded = set(excluded_utterances)
    seen = set()
    n_int = Counter()
    n_type = defaultdict(Counter)
    values = defaultdict(Counter)
    for utt, intent, entities in records:
        if utt in excluded or utt in seen:
            continue
        seen.add(utt)
        n_int[intent] += 1
        for slot_type in {t for t, _ in entities}:
            n_type[intent][slot_type] += 1
        for slot_type, filler in entities:
            value = " ".join(str(filler).split()).lower()
            if value:
                values[slot_type][value] += 1
    type_values = {t: [v for v, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:top_per_type]]
                   for t, c in sorted(values.items())}
    prior = {i: {t: round(c / n_int[i], 6) for t, c in sorted(n_type[i].items())} for i in sorted(n_int)}
    return {"type_values": type_values, "intent_type_prior": prior, "n_utterances": len(seen)}


def compose_values(intent: str | None, lexicon: dict, n: int) -> list:
    """Intent -> its slot types (prior >= MIN_TYPE_PRIOR, descending) -> round-robin over the types' most frequent
    values (each type descending by count), de-duplicated, capped at n. Unknown intent -> empty list."""
    prior = (lexicon["intent_type_prior"].get(intent or "") or {})
    types = [t for t, p in sorted(prior.items(), key=lambda kv: (-kv[1], kv[0])) if p >= MIN_TYPE_PRIOR
             and t in lexicon["type_values"]]
    out, taken = [], set()
    pointer = {t: 0 for t in types}
    while len(out) < n:
        progressed = False
        for t in types:
            vals = lexicon["type_values"][t]
            while pointer[t] < len(vals) and vals[pointer[t]] in taken:
                pointer[t] += 1
            if pointer[t] < len(vals):
                progressed = True
                taken.add(vals[pointer[t]])
                out.append(vals[pointer[t]])
                if len(out) >= n:
                    break
        if not progressed:
            break
    return out


def approx_tokens(text: str) -> int:
    return math.ceil(len(text) / APPROX_CHARS_PER_TOKEN)


def render_context(variant: dict, values: list, descriptions: dict) -> str | None:
    kind = variant["context"]
    if kind == "none":
        return None
    if kind == "type-vocabulary":
        return HEADER_TYPES + "\n" + "\n".join(f"- {t}: {d}" for t, d in sorted(descriptions.items()))
    if not values:
        return None
    return HEADER_TERMS + ", ".join(values) + "."


def fit_budget(variant: dict, values: list, descriptions: dict, count_tokens, budget: int = CONTEXT_TOKEN_BUDGET):
    """Render the context and drop trailing lexicon values until count_tokens(text) <= budget.
    Returns (text or None, tokens, kept_values, trimmed)."""
    kept = list(values)
    trimmed = 0
    while True:
        text = render_context(variant, kept, descriptions)
        tokens = count_tokens(text) if text else 0
        if tokens <= budget:
            return text, tokens, kept, trimmed
        if variant["context"] != "intent-lexicon" or not kept:
            raise InstrumentError(f"context of {variant['variant_id']} exceeds the {budget}-token budget ({tokens})")
        kept.pop()
        trimmed += 1


def bias_first_tokens(values: list, tokenize, bias: float) -> list:
    """First token of each value (as sentence start and as a mid-sentence word with a leading space), skipping
    stop words and very short first words; [[token_id, bias], ...], sorted, capped."""
    ids = set()
    for value in values:
        first = value.split()[0] if value.split() else ""
        if len(first) < BIAS_MIN_WORD_CHARS or first in BIAS_STOP_WORDS:
            continue
        for form in (value, " " + value):
            toks = tokenize(form)
            if toks:
                ids.add(int(toks[0]))
    return [[t, float(bias)] for t in sorted(ids)][:MAX_BIAS_TOKENS]


# ---------------------------------------------------------------------------------------------- sidecar I/O


def _post(port: int, path: str, body: dict, timeout: float = 600.0) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def sidecar_tokenizer(port: int):
    cache = {}

    def tokenize(text: str) -> list:
        if text not in cache:
            cache[text] = _post(port, "/tokenize", {"content": text, "add_special": False}, 60.0)["tokens"]
        return cache[text]

    return tokenize


def request_body(audio_bytes: bytes, context: str | None, decode: dict, bias: list, seed: int | None) -> dict:
    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": [
        {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio_bytes).decode("ascii"),
                                                 "format": "flac"}}]})
    body = {"model": "asr", "temperature": decode["temperature"], "max_tokens": BASE_DECODING["max_tokens"],
            "messages": messages}
    if bias:
        body["logit_bias"] = bias
    if seed is not None:
        body["seed"] = seed
    return body


def decoding_record(variant: dict) -> dict:
    return {**BASE_DECODING, "variant_id": variant["variant_id"], "variant_config_sha256": variant["_sha256"],
            "temperature": variant["decode"]["temperature"], "samples": variant["decode"]["samples"],
            "seeds": variant["decode"]["seeds"], "first_token_bias": variant["first_token_bias"],
            "context_kind": variant["context"], "lexicon_n": variant["lexicon_n"] if "lexicon_n" in variant else None,
            "context_token_budget": CONTEXT_TOKEN_BUDGET}


def check_ledger(repo: Path) -> None:
    ledger = (Path(repo) / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    rows = [ln for ln in ledger.splitlines() if LEDGER_ROW_ID in ln]
    if len(rows) != 1:
        raise InstrumentError(f"--full refused: exposure ledger must carry {LEDGER_ROW_ID} exactly once ({len(rows)})")
    row = rows[0].lower()
    if "consumed = no" not in row:
        raise InstrumentError("--full refused: the ledger row is not unconsumed (it must read consumed = no)")
    if "countersigned" not in row:
        raise InstrumentError("--full refused: the ledger row is not countersigned by the root")


def row_record(item: dict, variant: dict, status: str, text: str, seconds: float, usage: dict, ctx: dict,
               nbest: list | None) -> dict:
    row = {"schema": SCHEMA_ROW, "sample_id": item["sample_id"], "status": status, "transcript": text,
           "audio_sha256": item["audio_sha256"], "audio_seconds": item["audio_seconds"],
           "asr_seconds": round(seconds, 3), "completion_tokens": usage.get("completion_tokens"),
           "prompt_tokens": usage.get("prompt_tokens"), "variant": variant["variant_id"],
           "variant_config_sha256": variant["_sha256"], "context_chars": ctx["chars"],
           "context_tokens": ctx["tokens"], "lexicon_values": ctx["values"], "lexicon_trimmed": ctx["trimmed"],
           "bias_tokens": ctx["bias_tokens"], "intent_known": ctx["intent_known"]}
    if nbest is not None:
        row["nbest_count"] = len(nbest)
        row["nbest"] = nbest
    return row


def cmd_transcribe(a) -> int:
    data = Path(os.environ["SPEECHRL_DATA_DIR"])
    variant = load_variant(a.variant)
    doc, items = BASE.roster_items(REPO)
    if a.smoke == a.full:
        raise InstrumentError("choose exactly one of --smoke and --full")
    out_root = Path(a.out_root)
    out = out_root / a.model_id / a.variant
    if a.smoke:
        smoke_root = (data / "diagnostics" / "ASRBIAS-SMOKE").resolve()
        if a.rows is None or not 1 <= a.rows <= SMOKE_MAX_ROWS:
            raise InstrumentError(f"--smoke needs --rows 1..{SMOKE_MAX_ROWS}")
        if smoke_root not in out.resolve().parents:
            raise InstrumentError("--smoke writes only under $SPEECHRL_DATA_DIR/diagnostics/ASRBIAS-SMOKE/")
        items = items[: a.rows]
    else:
        check_ledger(REPO)
        if a.rows is not None:
            raise InstrumentError("--full runs the whole roster; --rows is a smoke option")
    session = json.loads((Path(a.session_root) / f"asr-sidecar-{a.model_id}" / "session.json").read_text())
    if session["model_id"] != a.model_id or session["device"] != "cpu":
        raise InstrumentError("sidecar session does not match the requested model or is not CPU")
    port = a.port or session["port"]
    lex = json.loads(Path(a.lexicon).read_text(encoding="utf-8")) if variant["context"] == "intent-lexicon" else None
    descriptions = type_descriptions()
    tokenize = sidecar_tokenizer(port)
    count_tokens = lambda text: len(tokenize(text))  # noqa: E731
    out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "transcripts.jsonl"
    if rows_path.exists():
        raise InstrumentError(f"{rows_path} exists; one-shot semantics, never overwritten")
    decode, n_samples = variant["decode"], variant["decode"]["samples"]
    peak, started, ctx_tokens = 0, time.time(), []
    with rows_path.open("w", encoding="utf-8") as sink:
        for item in items:
            audio = (data / item["media_relpath"]).read_bytes()
            if sha256_bytes(audio) != item["audio_sha256"]:
                raise InstrumentError(f"audio hash differs from the roster for {item['sample_id']}")
            intent = lex["row_intent"].get(item["sample_id"]) if lex else None
            values = compose_values(intent, lex, variant["lexicon_n"]) if lex else []
            text, tokens, kept, trimmed = fit_budget(variant, values, descriptions, count_tokens)
            bias = bias_first_tokens(kept, tokenize, variant["first_token_bias"]) if variant["first_token_bias"] else []
            ctx = {"chars": len(text or ""), "tokens": tokens, "values": len(kept), "trimmed": trimmed,
                   "bias_tokens": len(bias), "intent_known": bool(intent)}
            ctx_tokens.append(tokens)
            t0 = time.time()
            texts, usage, status = [], {}, "ok"
            try:
                for k in range(n_samples):
                    seed = decode["seeds"][k] if n_samples > 1 else None
                    reply = _post(port, "/v1/chat/completions", request_body(audio, text, decode, bias, seed))
                    usage = reply.get("usage") or usage
                    one_status, one = BASE.parse_asr_output(reply["choices"][0]["message"]["content"])
                    if one_status == "ok":
                        texts.append(one)
                status = "ok" if texts else "empty"
            except Exception as error:  # a failed contact is a recorded fact, never a silent retry
                status, texts, usage = f"error:{type(error).__name__}", [], {}
            seconds = time.time() - t0
            peak = max(peak, BASE.read_peak_rss_kib(session["pid"]) or 0)
            merged = SEP.join(texts) if n_samples > 1 else (texts[0] if texts else "")
            sink.write(json.dumps(row_record(item, variant, status, merged, seconds, usage, ctx,
                                             texts if n_samples > 1 else None), sort_keys=True) + "\n")
            sink.flush()
    decoding = decoding_record(variant)
    catalog = {"schema": SCHEMA_CATALOG, "package": PACKAGE_ID, "model_id": a.model_id, "variant": a.variant,
               "variant_config": {k: v for k, v in variant.items() if not k.startswith("_")},
               "variant_config_sha256": variant["_sha256"],
               "lexicon_sha256": sha256_file(Path(a.lexicon)) if lex else None,
               "type_descriptions_sha256": sha256_file(CONFIG_DIR / "slot-type-descriptions-v1.json"),
               "lock_entry": session["lock_entry"], "lock_revision": session["lock_revision"],
               "model_sha256": session["model"]["sha256"], "mmproj_sha256": session["mmproj"]["sha256"],
               "build_commit": session["build_commit"], "device": "cpu", "sidecar_argv": session["argv"],
               "split_identity_hash": doc["split_identity_hash"], "roster_dataset": BASE.DATASET,
               "rows": len(items), "transcripts_sha256": sha256_file(rows_path),
               "decoding": decoding, "decoding_sha256": sha256_bytes(canonical_json(decoding)),
               "context_token_budget": CONTEXT_TOKEN_BUDGET,
               "context_tokens_max": max(ctx_tokens) if ctx_tokens else 0,
               "context_tokens_mean": round(sum(ctx_tokens) / len(ctx_tokens), 1) if ctx_tokens else 0,
               "wall_seconds": round(time.time() - started, 2), "server_peak_rss_kib": peak or None,
               "created_at": datetime.now(timezone.utc).isoformat(), "mode": "smoke" if a.smoke else "full"}
    (out / "catalog.json").write_bytes(canonical_json(catalog))
    print(json.dumps({k: catalog[k] for k in ("model_id", "variant", "rows", "wall_seconds", "context_tokens_max",
                                              "context_tokens_mean", "mode")}))
    return 0


# ---------------------------------------------------------------------------------------------- lexicon build


def cmd_build_lexicon(a) -> int:
    sys.path.insert(0, str(REPO / "src"))
    sys.dont_write_bytecode = True
    data = Path(os.environ["SPEECHRL_DATA_DIR"])
    lock_path = Path(os.environ.get("SAEA_ASR_LOCK", BASE_LOCK_DEFAULT))
    E5 = _imp(REPO / "scripts/analysis/e5_transcript_consistency_read.py", "e5read")
    G = _imp(REPO / "scripts/analysis/gap_to_sota/gap_decomposition.py", "gapdec")
    lock = G.load_lock(lock_path)
    train = G.load_slurp_split(lock, data, "train", workers=4)
    gold_all = {}
    for r in train:
        G.guard(r.sample_id)
        gold_all[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario, "utt": r.utterance_id,
                                 "ents": tuple(G.SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
    pop = G.load_pop("FOLDB", G.POPS["FOLDB"], gold_all)
    fold_b = sorted(pop["rows"])
    fold_a, _ = E5.load_catalog(data, "fold-a")
    excluded = {gold_all[s]["utt"] for s in list(fold_a) + fold_b}
    lex = build_lexicon(((r.utterance_id, f"{r.scenario}_{r.action}", [(e.type, e.filler) for e in r.entities])
                         for r in train), excluded)
    del train
    lex["row_intent"] = {s: pop["rows"][s]["pred_intent"] for s in fold_b if pop["rows"][s]["pred_intent"]}
    lex.update({"schema": SCHEMA_LEXICON, "population_run": G.POPS["FOLDB"]["run"],
                "population_branch": G.POPS["FOLDB"]["branch"], "excluded_utterances": len(excluded),
                "fold_a_rows": len(fold_a), "fold_b_rows": len(fold_b), "top_per_type": TOP_PER_TYPE,
                "min_type_prior": MIN_TYPE_PRIOR})
    # scoring-side aggregate only: how often a row's gold value sits in its own composed lexicon
    recall = {}
    for n in (30, 100):
        hit = tot = 0
        for s in fold_b:
            vals = set(compose_values(lex["row_intent"].get(s), lex, n))
            for entity in gold_all[s]["ents"]:
                tot += 1
                hit += int(" ".join(str(entity.filler).split()).lower() in vals)
        recall[str(n)] = {"gold_items": tot, "in_lexicon": hit, "rate": round(hit / tot, 4) if tot else None}
    lex["gold_value_in_lexicon_aggregate"] = recall
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(canonical_json(lex))
    print(json.dumps({"out_sha256": sha256_file(Path(a.out)), "types": len(lex["type_values"]),
                      "intents": len(lex["intent_type_prior"]), "utterances": lex["n_utterances"],
                      "excluded_utterances": lex["excluded_utterances"], "rows_with_intent": len(lex["row_intent"]),
                      "gold_in_lexicon": recall}, sort_keys=True))
    return 0


BASE_LOCK_DEFAULT = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "score":  # unchanged scoring path
        try:
            return BASE.main(argv)
        except BASE.InstrumentError as error:
            print(f"asrbias_foldb: REFUSED: {error}", file=sys.stderr)
            return 3
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-lexicon")
    b.add_argument("--out", required=True)
    t = sub.add_parser("transcribe")
    t.add_argument("--model-id", required=True, choices=("qwen3-asr-0.6b", "qwen3-asr-1.7b"))
    t.add_argument("--variant", required=True, choices=VARIANT_IDS)
    t.add_argument("--out-root", required=True)
    t.add_argument("--lexicon")
    t.add_argument("--rows", type=int)
    t.add_argument("--smoke", action="store_true")
    t.add_argument("--full", action="store_true")
    t.add_argument("--port", type=int)
    t.add_argument("--session-root", default=os.path.join(os.environ.get("SPEECHRL_DATA_DIR", "."), "serving"))
    a = p.parse_args(argv)
    try:
        return {"build-lexicon": cmd_build_lexicon, "transcribe": cmd_transcribe}[a.cmd](a)
    except InstrumentError as error:
        print(f"asrbias_foldb: REFUSED: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
