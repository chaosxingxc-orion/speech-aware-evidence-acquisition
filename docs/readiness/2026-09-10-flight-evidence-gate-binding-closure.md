# Shared evidence gate binding closure

The root judge worker at source 99271e80 was refused before its attempt opened.
The dataset already declares the inherited participant-name D1 supplement; FlightRuntime
omitted both evidence supplement arguments at its generation and preparation gate constructors.
The six-line shared fix forwards the same registered values at both sites. It changes no
fragment, source bytes, prompt, selected slice, capacity request, generation budget or service.

The unused judge run/attempt pair remains available. No generation occurred. The sole old
attach receipt is preserved byte-for-byte in
SPEECHRL_DATA_DIR/coordination/e21-loop-judge-precontact-original-attach-v1.json.
The closure and absence-of-attempt observation are in
coordination/e21-loop-judge-d1-precontact-closure-v1.json.
A later failure after attempt creation must not reuse this one-time key.

Regression coverage exercises both gate constructors with and without an evidence
supplement. The participant-name identity and D1 supplement contract tests remain unchanged.
An existing factory test fixture now supplies its missing data root so that its intended
adaptive-window refusal reaches the existing validation. No production behavior is changed
for that fixture correction. Existing capacity fits remain valid because no request bytes or
service identity changed.
