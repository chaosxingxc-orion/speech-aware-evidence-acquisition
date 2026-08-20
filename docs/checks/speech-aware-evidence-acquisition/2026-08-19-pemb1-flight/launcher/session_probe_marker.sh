#!/usr/bin/env bash
# Model-free binary inspection: locate the mtmd media-marker literal and the
# /props field name in the receipt-pinned llama.cpp build. Spawns nothing, loads
# no model. This is the evidence that LLAMA_MEDIA_MARKER='<__media__>' is the
# pinned build's own default rather than a guess -- the VALUE is still
# re-verified fail-closed against the live server's GET /props before the first
# embedding contact (rails.embedding_client.EmbeddingClient.verify_media_marker).
TRI=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2
BIN=/home/chao/llama.cpp-featcache/build/bin
exec > >(tee "$TRI/marker-probe.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "pinned build: $BIN"
sha256sum "$BIN/llama-server"
echo
echo "=== media marker literals in the pinned build ==="
for f in "$BIN"/llama-server "$BIN"/*.so*; do
  m=$(strings "$f" 2>/dev/null | grep -oE '<__[a-z_]+__>' | sort -u | tr '\n' ' ')
  if [ -n "$m" ]; then echo "  $(basename "$f"): $m"; fi
done
echo
echo "=== 'media_marker' /props field name present? ==="
for f in "$BIN"/llama-server "$BIN"/*.so*; do
  if strings "$f" 2>/dev/null | grep -qx 'media_marker'; then echo "  present in $(basename "$f")"; fi
done
echo
echo "=== embedding-mode flags available in this build ==="
"$BIN/llama-server" --help 2>&1 | grep -iE '^\s*--embedding|^\s*--pooling|--embd-normalize' | sed 's/^/  /'
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
