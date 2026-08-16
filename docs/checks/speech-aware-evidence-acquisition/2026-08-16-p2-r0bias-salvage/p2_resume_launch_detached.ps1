# PHASE 2 R-ladder RESUME (four un-run arms) detached launch.
# Plan rule I1: no harness task cap can kill it (block is ~9-10 h).
$script = "/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad/p2_resume_launch_only.sh"
Start-Process -WindowStyle Hidden -FilePath "wsl.exe" -ArgumentList @("-d", "Ubuntu-24.04", "bash", $script)
Write-Output "P2 R-ladder RESUME launched detached at $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')); progress log: WSL /home/chao/p2-rladder-detached-*.log"
