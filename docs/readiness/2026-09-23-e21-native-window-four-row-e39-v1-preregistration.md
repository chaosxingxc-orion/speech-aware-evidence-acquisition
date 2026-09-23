# Item E39 four-row dry run on the E21 native-window cell: preregistration

Registered 2026-09-23 before any contact, by the E39 registration agent (Fable 5.1),
in the worktree `/home/chao/saea-worktrees/fable-e39reg` (branch `fable/e39reg`, base
commit `321b64fe`). **Development receipts only -- no score, no number, no claim beyond
the three assertions fixed below.**

Authority: `docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`
section 5 (the dry-run sketch), `docs/results/2026-09-22-base-lock-v3.md` section 5a
(the one open harness defect at the lock), owner decisions 89 and 98.

## 1. The defect this cell tests a repair for

E35 exposed that item E13's `finite_completion_policy = deliver-latest-or-abstain` is
scoped to the **whole episode**: a `length`-truncated contact on a **non-answering**
node ends the episode with no Solver draft and delivers the empty string. On the E35
sub10 arm that hit 75 of 342 windows, whose 76 empty deliveries carry 95.6 % of the
arm's extra error mass; removing them moves the arm from 0.2864 to 0.0778 corpus WER.
Those numbers are the E35 read's, quoted as the reason this cell exists. **This cell
re-measures none of them.**

## 2. The cell

| item | value |
| --- | --- |
| base | the sealed `e21-native-window-system-four-row-v1` as its `recovery-v4` attempt flew it (flight commit `1a9c78d2`) |
| factor | one repair, three leaves: `finite_completion_scope` `episode` -> `answering-node`; `roles.perception.max_completion_tokens` 320 and `roles.reviewer.max_completion_tokens` 384; Reviewer probe v2 (tool-free) for v1 |
| unchanged | roster (4 native windows of call `4320211`), geometry (np4 x 24,576, `max_tokens` 1024), session, six-node graph, contact ceiling 11, no `phase_tools`, no `knowledge_stores`, execution-unit subset, window feature packets, knowledge snapshot, task instruction, Perception / Solver / Planner probes |
| comparator | the sealed E35 four-row **system** arm -- **receipts only**, never re-flown, never re-scored |
| margins | none. There is no score and therefore no margin, no own-null and no bar |
| runs | `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39-V1` (44 calls) and `...-FIT-V1` (176 endpoints) |
| ceilings | 44 calls / 176 fit endpoints / 3,960 repeated speech seconds / 0.5 GPU hours / **0** official scoring jobs |
| authority | E35 read section 5; base lock v3 section 5a; owner decisions 89, 98 |

`finite_completion_policy` stays `deliver-latest-or-abstain` and
`react_exhaustion_policy` stays `continue-without-answer`, the two keys
`scripts/checks/finite_completion_policy_check.py` requires of every live unflown
native cell. Neither value moves; only the **scope** the first applies to.

## 3. Decision rule (fixed here, before contact)

The rule is the E35 read's section 5 dry-run sketch, stated as three receipt
assertions over the sealed manifest. **PASS iff all three hold.**

- **R1 -- no auxiliary node voids its window.** ZERO retained rows carry a
  `terminal_disposition` whose `role_id` is `perception` or `reviewer` together with an
  abstention. Under the answering-node scope a truncated non-answering node keeps its
  truncated note and the Solver still answers. A single such row **FAILS**.
- **R2 -- every window delivers.** 4 of 4 windows deliver **non-empty** text: one
  `saea-deliver-earnings-text-v1` delivery receipt per window, zero blank deliveries.
  Fewer than 4 **FAILS**.
- **R3 -- the per-role caps hold.** ZERO Perception or Reviewer contacts end with
  `finish_reason = length` at the 320 / 384 caps. This count is **reported with its
  exact value on every verdict**; a non-zero count is a **named cause** carried into
  the next registration, never a silent pass.

The sealed comparator abstained on **two** of these four windows and completed
REVISE/ACCEPT on the other two, which is the contrast the read will table: the same
four windows, the same graph, receipts beside receipts.

**No score enters this rule.** The campaign schedules zero scoring jobs and the verdict
document quotes no metric.

## 4. Consequence

On **PASS** the repair is proposed to the owner as **base lock v3.1** (base lock v3
section 5a), keeping every sealed configuration byte-identical by default: the scopes default
to `"episode"` and the per-role caps default to absent, so no sealed cell's request
bytes move and the SLURP locked plan is not re-flown. On **FAIL** the repair stops
here, the named cause is registered, and nothing else flies on it.

## 5. What is not claimed

No score, WER, entity-WER, numeric-accuracy or semantic-error-rate claim. No
effectiveness, superiority, comparison or generalization claim -- n = 4 windows of one
call, far below the paired-effectiveness floor of n >= 400. No claim that the repair
helps the sub10 or full-discovery E21 read; the descriptive HARM the E35 read recorded
is not re-read, re-scored or revised. No claim about SLURP or Audio2Tool. No Stage-3
claim, no module admission (harness-admission label `NONE`), and no paper-scale claim
of any kind. No delivered utterance or transcript text is printed or persisted by the
read.

## 6. Budgets and failure rule

Ceilings, never targets: 44 generation calls (4 windows x the eleven-contact program
maximum), 176 fit endpoints (44 x (1 speech packet + 3 endpoints)), 3,960 **repeated**
speech seconds (4 x 11 x 90 s -- every native-episode contact re-sends the window
audio), 0.5 GPU hours, zero official scoring jobs, zero ASR / encoder / paid-API calls,
zero native task-contract calls. The sealed comparator realized 13 contacts / 1,170
repeated seconds on these same windows.

First failure stops and preserves the original failure and contact record: no automatic
restart, replay, row filtering, roster, role-graph, prompt, knowledge, geometry or cap
change. **At most one** separately registered recovery after a named cause and a
bounded proof; a second failure stops the flight and the fix is proven on a fresh
four-row dry run first.

## 7. Registration state

Readiness is **HELD**. Root mints
`coordination/e21-native-window-four-row-e39-v1/root-admission-v1.json` (decision id
`e21-native-window-four-row-e39-admission-v1`), flips and re-pins with
`scripts/flights/repin_cell.py`, switches the resident serving geometry to
`serving-e21-native-window-flightruntime-np4-max1024-v1` and enqueues the cell on the
SAEA-Batch-Driver (decision 77). The flip moves the composed config hash
(`b2d60c63...`) and the protocol hash (`9b927445...`) recorded in this package; the re-pin
tool rewrites them here, in the plans, in the protocol document, in the README and in
both exposure-ledger rows. Runbook:
`docs/readiness/2026-09-23-e21-native-window-four-row-e39-v1/README.md`.
