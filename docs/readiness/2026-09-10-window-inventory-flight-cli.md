# Exact-window inventory flight entry point

Status: engineering seam implemented; neural feature materialization remains held.

The shared flight CLI now exposes prepare-window-inventory as a distinct
model-free campaign stage. A campaign cell must name that stage explicitly.
The command composes the registered model, dataset, baseline, and experiment
fragments through FlightRuntime, builds the existing ExecutionPlan, and uses
FlightRuntime.materialize_window_batch to construct the registered exact-window
requests. A cell with no valid execution plan is refused before window
materialization.

The runtime derives WindowFeatureEncoderIdentity from the committed runtime
receipt. It hashes the receipt with a before-and-after file identity check,
confines the runtime binary and model files to their configured roots, and
verifies their declared byte sizes and SHA-256 values against the actual
files. Legacy receipts must identify exactly one decoder GGUF and one file
whose filename contains mmproj; the llama.cpp build commit is also required.
No hash is accepted from a CLI argument.

The resulting artifact is written only to the explicit output path through
prepare_window_feature_inventory. This path performs no service lookup or
launch, session lease, tokenizer access, encoder execution, scorer execution,
or model request. It records verified source windows and a pinned encoder
identity; it does not state that encoded feature files exist.

Remaining work is separately gated. A successor experiment cell must declare
prepare-window-inventory and retain a valid execution plan. Feature encoding,
strict cache promotion, and the refusal-before-encoding serving boundary still
require their own implementation, synthetic validation, runtime qualification,
and owner admission.
