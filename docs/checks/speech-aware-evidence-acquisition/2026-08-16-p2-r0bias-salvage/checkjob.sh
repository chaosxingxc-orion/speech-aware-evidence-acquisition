S=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad
echo "--- running score processes ---"
pgrep -af score_r0bias.py || echo none
echo "--- log size ---"
ls -l "$S"/score_r0bias.log "$S"/r0bias.*.json 2>/dev/null || echo "no outputs yet"
