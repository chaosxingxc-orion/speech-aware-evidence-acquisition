# Incident: confirmatory-split touch during a Q4 throughput probe (2026-08-09)

Status: **RECORDED, owner decision pending.** Filed the moment the ops agent
self-reported. Ledger row: `SAEA-INCIDENT-2026-08-09-CONFIRMATORY-TOUCH`.

## What happened

A throughput probe of the newly requantized Q4_K_M model was run **outside**
the governed driver (raw llama-server HTTP, no `ExecutionPlan`, no gate — a
plain ops measurement) and used carrier sample
`earnings22-original/4420696` for its test slices. That id is in the
**confirmatory** split (`docs/receipts/splits.json`, 115 ids), not dev.

Exposure, stated exactly:
- 10 model calls, 600 s of metered audio, 7 distinct 60 s windows
  (offsets 120/300/600/900/1200/1500/1800 s; the 120 s window 4×)
- **2 full transcripts were surfaced into the operator conversation** — the
  content was READ, not merely produced
- No `ExecutionPlan`, no gate check, no pre-registered ledger row at touch
  time; nothing written into the repository

## Why it is a breach

- `docs/receipts/splits.json`: confirmatory ids "remain unread; any
  confirmatory result read requires Stage-3 authority or a dated owner
  allowance (consolidated contract §7)"
- `docs/exposure-ledger.md` header: confirmatory rows "require Stage-3 paper
  authority … and do not occur in Stage-2"; `consumed` is "**irreversible
  once `yes`**"

The retroactive row therefore carries `consumed = yes` for that id.

## Cause (implementer fault)

The task brief for the ops agent said to cut a test slice from "a sample in
`earnings22-original`" **without restricting it to the dev split**. The agent
selected by scanning the media directory. The frozen split receipt was not
consulted because nothing in the brief or the raw-HTTP path required it —
the governed driver would have refused this automatically (its
`load_split` → plan → gate chain binds every request to a verified split),
but an out-of-driver ops probe has no such rail.

The agent discovered the breach itself while preparing the next task, checked
`splits.json`, and reported it unprompted. That self-report is the reason
this record exists at all.

## Scope and residual integrity

- **1 of 115** confirmatory ids affected; the other 114 remain unread.
- The affected id's content is now known to the implementer conversation, so
  any future confirmatory use of `4420696` would be contaminated.
- No discovery/dev split integrity is affected. The Q4-vs-Q8 quality
  comparison that followed used dev subset10 only and is clean.

## Owner decision required

1. **(a) Dated owner allowance**: keep the split as frozen, record this
   exposure permanently against `4420696`, and accept that Stage-3 analyses
   must either exclude that id or disclose the prior exposure.
2. **(b) Retire the id**: remove `4420696` from the confirmatory split,
   re-freeze `docs/receipts/splits.json` with a new identity hash (114 ids),
   and record the reason. Cost: the frozen split hash changes, so any future
   reference to the old hash must be read as historical.
3. **(c) Owner's alternative.**

Until this is ruled on, no confirmatory-split work proceeds; all Stage-2
experiments continue on discovery/dev only (which is where they already are).

## Preventive fix (implementer, applies immediately)

Every ops/benchmark task brief that touches carrier audio must name the
**exact split and ids** the probe may use, drawn from
`docs/receipts/splits.json`, and must state that any other id is out of
bounds. Raw-HTTP probes get the same discipline as governed runs: the
governed driver enforces it mechanically; out-of-driver probes rely on the
brief, so the brief must carry the constraint explicitly.
