"""E0 model-free closure: deliverable artifact generators and the closure receipt.

Every generator here is model-free by construction: it reads carrier layers, lock
entries, contract code and local file bytes; it never opens a model endpoint, never
decodes audio and never copies annotation content into an artifact. Artifacts land
under ``docs/receipts/artifacts/`` and are bound into ``docs/receipts/e0-closure.json``
whose hashes ``contracts.FrozenCoreGate`` re-verifies before any model touch.
"""
