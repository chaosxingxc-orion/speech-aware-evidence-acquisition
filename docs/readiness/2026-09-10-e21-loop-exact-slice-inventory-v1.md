# E21 LOOP exact-slice inventory preparation

This model-free preparation materializes the sealed judge and matched-random LOOP plans through the shared `FlightRuntime.prepare_window_inventory` path. Each arm must yield 600 selected slices across all 44 frozen discovery calls and total 15,340.460005376464 seconds. The plan loader re-proves each selected span and predecessor word range before the shared cutter writes and hashes the actual WAV slice.

The two artifacts remain separate because each plan owns different request identities. After both succeed, the closure receipt compares their source audio SHA-256 and encoder keys to report union deduplication across arms. No count declared in this file can substitute for the actual source-bound artifact rows.

This preparation reads the sealed historical predecessor needed to construct each request tail. It opens no reference layer and makes no model, server, encoder, tokenizer or scorer contact. It does not choose a serving geometry, qualify packet transport, authorize fitting or generation, or modify the held LOOP successor.
