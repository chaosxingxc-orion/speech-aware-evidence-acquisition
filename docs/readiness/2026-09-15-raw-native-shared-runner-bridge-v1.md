# Raw speech native shared-runner bridge

Use the explicit raw-speech-agent-native-tools D2 arm with native-raw-speech-v1 transport order. The shared run_speech_native_agent_loop accepts query_source='speech_audio'; its default remains speech_features. The existing speech_packet_bindings map carries each raw media path in packet_id and its SHA256. No feature packet is manufactured.

The client admits only the adapter-bound original source or a registered SliceRecord for that sample. It verifies the hash before fit/preparation and again before dispatch. The transport checks the actual bytes embedded on the wire. Native tool results retain the raw query path/hash custody. Tool schemas, registered evidence IDs, state history, counted requests and Solver answer authority use the existing shared OpenJiuwen path.

Root reviewed the data-source selector, same-sample slice checks, raw/feature mutual exclusion, native history and actual public-runner regression. The final focused suite passed247 tests; Ruff, engineering-base and diff checks passed. Earlier client/transport/slice suites passed as reported in the implementation review. No research model or GPU contact occurred.

This supplies the raw client/transport/public-runner route. E21 still needs its window inventory and FlightRuntime caller connected to this route before a native E21 experiment can be registered. No production E21 configuration, segmentation rule, model input protocol, scoring definition or dispatch permission is changed by this bridge.
