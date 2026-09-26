# First system-learning batch: closed without a memory update

## Whole-system execution and disposition

The construction batch contains four frozen TRAIN inputs and four complete
Perception/Solver/Reviewer/Planner trajectories per input. All 16 episodes
sealed with 67 generation contacts and one official score per complete actor
manifest. All 16 trajectory summaries finalized. One terminal-disagreement
group then completed semantic comparison and group-update generation.
Three tied groups retained their registered no-update disposition.

The final group-update artifact sealed at 2026-09-26T09:10:52Z under frozen
worker a2473a3dfa69c119c3d28c12c6648aa10d189b98. Root registered reading,
recursively verified the sources, and retained the unmodified raw response.

The updater emitted a fenced JSON array containing three UPDATE operations.
Each ID was a whole generated lesson, not an existing record. The actual
model-facing existing_experiences and verified frozen pool were both empty.
The strict parser first rejects the fence. Root's diagnostic removal of only
the fence exposes three independently invalid targets, with ID lengths
695, 664 and 648 characters. No corrected array was published or consumed.
The source request was 9779 tokens; generation ended normally after 751 of
2048 available output tokens. Neither truncation nor memory pressure explains
this structural failure.

The shared batch preparer preserved all four inputs, produced zero contexts,
and returned no-change-no-operation. No batch synthesis generation, forced
ADD conversion, repair retry or new memory activation followed. The frozen
empty pool's successor digest equals its base digest. The closure is
docs/receipts/continuation/2026-09-26-system-batch001-no-update-closure.json.

| Construction stratum | Inputs | Terminal ties | Invalid update groups | Valid updates |
| --- | ---: | ---: | ---: | ---: |
| alarm | 1 | 1 | 0 | 0 |
| audio | 1 | 1 | 0 | 0 |
| datetime | 1 | 0 | 1 | 0 |
| takeaway | 1 | 1 | 0 | 0 |

This is a construction/protocol diagnostic, not an effectiveness screen.
Natural-mixture and equal-stratum task-effect estimates are not newly computed;
four inputs cannot establish improvement or generalization. Official source
scores remain unchanged and are not rerun.

## Distinct defects and why they matter

1. **Actor capability/instruction mismatch.** The initial tool-free actor
   retained a prompt demanding a task-contract tool. This is an engineering
   confound; both future learned and empty-memory controls must receive any
   correction uniformly. Do not attribute that repair to learning.
2. **Semantic credit fidelity.** Summaries and comparison treated Reviewer
   assertions as actual tool events, lost the initial-versus-revised intent
   transition and misread entity counts as intent evidence. The proposed
   guidance consequently recommends reliance on nonexistent tool results.
3. **Memory operation identity.** The updater treated proposed lessons as
   already stored records, even though the pool was empty. Syntactic stripping
   alone cannot fix it. Invalid updates do not demonstrate that no useful
   experience exists; they show that this executed learner did not create one.

The baseline learning chain has now reached an explicit no-update terminal
state. No stable training-free RL gain has been demonstrated.

## Next bounded comparisons

Use the existing shared controller and registered response-format path to
prospectively constrain operation syntax and targets to the exact frozen pool.
Keep generated source lessons, prompt content and decoding settings fixed for
that interface test. An empty pool permits ADD or NONE, never UPDATE or DELETE.
This is a named interface correction, not an algorithmic quality claim. Bind the
format to actual prepared memory, and check real fit including grammar handling.
Preserve the current output and do not restart its completed attempt.

Separately test event-grounded semantic credit against the sealed baseline:
hold actors, summaries, feedback and decoding fixed; supply mechanically
verified actual tool events, chronological role outputs/control transitions,
and explicit metric definitions. Do not inject root-written desired lessons
or reference task answers. Measure fidelity before claiming task improvement.

Then freeze valid candidate memory and a matched empty-memory policy for the
next disjoint construction batch. Correct role/tool capability declarations in
both. Update only at the next batch boundary. Full-system task evaluation and
same-roster replication remain necessary; local validity or fidelity is not a
substitute. Keep 32-input batches unfrozen, and size any later increase using
the complete actor-to-memory chain, measured token demand and host/GPU margins.

## Resource and prefix boundaries

The actor service used two 24576-token slots; semantic stages used one
49152-token slot with the same total context. All remain decoder-only,
no-mmproj, with verified precomputed speech features. The actor prefix audit
found 16 role/visit common-prefix groups identical and four Perception message
groups identical. Seeds live in decoding parameters; per-trajectory history
must not be replaced to manufacture cache reuse.

The group-update campaign had 41 guard observations. Peak GPU
allocation was 20456 MiB, minimum GPU free memory was
3682 MiB, and minimum Windows available memory was
29.905 GiB. All decisions admitted work.

The resource guard closes contact admission below 12 GiB host availability
and stops the owned service below 10 GiB; GPU admission/stop floors are
2048/1024 MiB. Sampled protection is not a guarantee against sudden external
allocations. No power-mode changes were made.
