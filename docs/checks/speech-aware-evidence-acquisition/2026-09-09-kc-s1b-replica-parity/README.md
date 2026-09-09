# KC-S1b complete request parity

All 1,000 historical completed-attempt MODEL_REQUEST payloads match current shared
FlightRuntime.materialize_phase_requests() output after removing only request_id and
decoding_params.id_slot. Both normalized roster hashes are
f5710feb4d222963e47bd6a2fdebad6c8bcb70fc9e7ad9ee3c68a18fe5fea1df.
There are zero missing, extra or changed rows. System instruction, history/predecessor,
schema fill, evidence, packet identities and decoding parameters remain identical.

The historical manifest and raw trace hashes were verified before extracting request
records. The current requests were obtained through the shared controller/OpenJiuwen
contact-free transport, not a separately reconstructed prompt. Raw payloads remain in
the data root and never enter Git. No real model, tokenizer, encoder or scorer was used.

This closes payload parity. Verify the transport rendering/runtime identity, prospectively
register the capacity check and generation, and bind a full fit receipt before generation.
