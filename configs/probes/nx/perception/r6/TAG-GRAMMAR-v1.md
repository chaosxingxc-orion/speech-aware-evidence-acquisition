# NX R6 Perception distinction tag grammar v1 (pinned text; the reader parses exactly this)

Scope: the `distinction` string of EVERY candidate in a `slurp-intent-hypotheses-v1` note (128 characters at most,
enforced by the registered response format). The v1 contract admits no other field, so the tag lives at the head of
the distinction. ASCII only.

```
distinction := presence [ mentions ] "; " words
presence    := "E=" ( "none" | "some" | "unsure" )
mentions    := ( "; M=" words ){1,3}
words       := one or more English words separated by single spaces (no ";" inside)
```

* `E=none`   the current speech expresses no entity value (no named item, place, person, date, time, number or quantity).
* `E=some`   the current speech expresses at least one entity value.
* `E=unsure` the speech is too short or unclear to tell (admitted only by templates that allow it; otherwise `invalid`).
* `M=<words>` the exact words heard for one entity mention, in spoken order, at most three mentions, each at most 4
  words; present only when `E=some` (an `M=` after `E=none` is `invalid`).
* The trailing `words` are the speech-grounded distinction of at most 8 English words.
* Parse classes per candidate: `ok` (grammar matched), `absent` (no `E=` head), `invalid` (head present but the
  grammar fails, a value outside the allowed set, or a mention after `E=none`). The rank-1 candidate's tag is the
  node verdict; the list majority is reported beside it.
