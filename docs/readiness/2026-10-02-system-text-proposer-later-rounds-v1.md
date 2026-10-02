# Later-round proposer execution readiness

Recorded 2026-10-02T03:32:11.530406+00:00 by ChatGPT root under owner decisions214/215/217. This is offline engineering evidence; it does not admit a proposal or a GPU flight.

## Repair

The launcher validated only the four round-one keys, interpreted a closed slot as a round-one allocation and imported every response into round one. That made the registered second and third updates unusable despite the archive and offline exporter supporting them.

The launcher now accepts an explicit `round_index` of1,2 or3 and requires all four original branch/slot identities from that same round. Legacy round-one registrations retain their omitted-field default. It checks failed-slot dispositions against the exact round and imports into the packet's branch, round and slot. For later L inputs, the preceding feedback family must match the round and its whole-family hash must agree with the recorded parent selection. The existing offline exporter still revalidates the complete seals, official scores and exact root READ before creating any real learning capsule. These checks do not replace that exporter gate. B remains feedback-free and uses the original seed.

## Verification

The test-first reproduction had9 failures and14 passes. After the repair,243 related tests pass across launcher, capsule isolation, paging, actual local HTTP/SSE transport, source feedback, archive, stage, selection and protocol. Launcher statement coverage is94%; Ruff and the engineering-base check pass. Synthetic launcher tests exercise all four round-two and round-three allocations through real one-shot dispatch and archive import, while replacing credentials and the remote model with a deterministic local response. No remote model, tokenizer, GPU or scorer contact was added.

## Remaining input-budget issue

The preserved L-1-2 attempt made two metered material-reading calls and used11394 input/129 output tokens. It had21374 input tokens remaining when the third call was refused. Reconstructing that third request offline from the exact retained response and capsule yields a conservative input bound of44859 for the requested13500-character terminal-output page. Even a hypothetical one-character page yields28573, because the request carries the earlier context and6500-character read again. This is an admission-bound failure, not proof of an actual provider token overrun.

Reducing only the second page cannot solve that observed failure. Before round-two proposal admission, verify a compact, auditable multi-turn feedback package against the unchanged32768-input/4096-output/four-contact allocation. Preserve complete source evidence and explicit indexing/omission records; do not repair the prior failed proposal, substitute another slot, raise budgets, or give B any feedback. No new packaging or proposer contact is admitted by this report. The current launcher repair alone is not full round-two readiness.

## Live experiment boundary

At03:29:29Z, update1 L-parent was OPENED with1592 actual model contacts; the remaining four400-row members had not started. These contacts are not completed-row counts. The registered process243879 was verified from its current command line, STOP was absent, the server was healthy with4 slots busy, GPU usage was22976MiB at92%, and Windows free memory was13.23GiB.

The active worker remains frozen at2f07dd3d6f52eee79d24243c40a0dff195260816. This repair is prospective only. The five-member update1 READ remains unsigned; no partial scientific results were read. Other held carriers and failed artifacts retain their existing dispositions.

Evidence: [machine-readable receipt](../receipts/continuation/2026-10-02-system-text-proposer-later-rounds.json).
