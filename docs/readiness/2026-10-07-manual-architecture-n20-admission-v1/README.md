# Manual architecture N20 preregistration

This source change adds the explicit `manual-architecture-n20-v1` selector to the existing generation/FIT registration path. It does not dispatch work or authorize a result read. The existing TaskAdapter, FlightRuntime, official scorer, exposure ledger, source checks and complete-family reader remain the execution path.

Use the original pinned architecture population and its declared member order: seed, seed-aa, review-off and solver-lookup. Derive roster size and budgets from that population. The current declaration has twenty rows per member, generation ceilings 260/260/40/60, and FIT ceilings 1040/1040/160/240. One official scoring job per complete manifest is planned; scoring and subsequent scientific READ retain their existing separate gates. This twenty-row form proof does not establish benefit.

Both ordinary registered plan schemas must bind their exact composed configuration, configured roster, production runtime order, policy, prepared supply, execution plan, population budget and root decision. Add `architecture_proof`, `preparation_receipt`, `natural_prerequisite` and `decision_receipt` to the prospective successor plans. Keep all historical drafts, receipts and partial attempts unchanged.

`natural_prerequisite` contains exactly two DATA pins, `registration` and `qualification`. The qualification must cover all four configured members and carry the root structural READ pin. Admission independently checks the original natural configs and policies, configured/runtime membership, original manifests and attempts, completed owned guard terminals, custody inspections, structural reports and actual FIT artifact/journal accounting. The natural root admission must name its exact eight eligible IDs and the same original C4 capacity pins. Neither a status string nor one successful member substitutes for this chain.

Each `preparation_receipt` is a raw repo pin to the fresh existing producer receipt. Bind current config/run/attempt/policy/supply, zero preparation contacts, warm verification, output equality, runtime order and `prepared_source_commit`. Require the current prepared envelope's exact config identity, packet membership, output seal and five implementation hashes. The equality source is the corresponding original qualified C4 capacity envelope. Require runtime order to match that original capacity's prospectively bound order; legacy capacity retains its exact configured-order rule.

The root N20 decision remains `saea-campaign-decision-v1`, status `decided`, owner decision 227, with `learner_export: false`, exact population/capacity/natural pins, `source_preparation_commit`, and all eight N20 generation/FIT IDs in declared member order. Both plans carry its same raw DATA pin. This permits later registration-only commits without waiving any hashed runtime source check.

Root must first repin the existing N20 envelopes against the streaming source with unchanged outputs, author/countersign the prospective plans and exposure rows, and run the existing named gate before freezing or dispatch. For each declared member, use the existing command from the selected frozen repo:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$WORKER/src" \
  /home/chao/.venvs/speechrl/bin/python -B \
  "$WORKER/scripts/checks/flight_registration_check.py" \
  --repo-root "$WORKER" --data-root "$SPEECHRL_DATA_DIR" \
  --cell slurp-native-stage3-simple-consumption-seed-n20-v2 --json
```

Replace only the member label for the other three cells. The gate still checks root receipts, registered exposure, analysis recipes and READ rows; this selector does not bypass them. Runtime's existing strict prepared-artifact check and root's fresh service/resource/control admission remain required. The shared batch campaign path is the dispatch route after those gates; this engineering package does not change it.

Engineering ownership: GPT-6.1 Sol implements and tests. GPT-6 Astra/Ultra independently reviews and plans. Root coordinates admission, serial integration, freezing and launch. No model/tokenizer/scorer contacts, task answers, quality reads or live controls were used for this change.
