# Semantic value supply correction before the dual-store flight

The full-roster preparation found eight ranked keys but zero supplied values. All
1,000 query/packet IDs and all 60 facet/vector IDs aligned. The inherited
saea-fuse-supplyfilter-v1 intentionally requires an answer-bearing task_target;
the released semantic intent-boundary values intentionally have no such target.
That legacy fuser is unsuitable for this content, although its historical behavior
is correct for its original experiment contract.

Root added the opt-in registered saea-fuse-associated-values-v1 to the shared
knowledge policy module. It admits the first m ranked facets by cosine threshold,
traverses them in rank order, supplies at most c unseen associated values per
facet in stable value-ID order, deduplicates across facets, and stops at top_l
values overall. This version sets m=8, c=1, top_l=8, and tau=0. It never
requires or invents an answer label. Solver remains the answering authority.

The old fuser and sealed store bytes remain unchanged. The empty preparation is
preserved and rejected before model contact. No task quality was read. A fresh
artifact must pass full1000 nonempty supply and live/warm selection equivalence
before generation. This fixes implementation of the prospectively intended
semantic supply; it is not a response to task-quality results.

Rejection receipt: DATA/coordination/slurp-direct-vs-native-dual-store-dev1000-v1/
preparation-rejection-v1.json, SHA256 ac0d7549462caff9ae8c59ace3d494b061757539ee82e4dfc0254a0eb7c48be9.
