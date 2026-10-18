# Windows-side orchestrator of the 322 window (owner rulings 322 A / 331 A, 2026-10-18). `wsl --shutdown` kills every WSL process, so the
# window is driven from Windows: wait for CHAIN_NXT2_EXIT rc=0 after the R2 rec2 chain start -> pre-shutdown step (no flight; stop the
# resident serving session) -> back up and edit .wslconfig (memory 44GB -> 36GB) -> wsl --shutdown -> restart -> post-restart step
# (close R2 rows, swap to think-budget-np4, diagnostic, R3 hook). Any other R2 exit, a refused pre-step, or a timeout leaves everything as is.
param([string]$Stamp = '2026-10-18T14:36:38Z', [int]$PollSeconds = 120, [int]$MaxWaitSeconds = 129600)
$Q = '/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch/queue'
$Log = 'D:\wsl\w322-orchestrator.log'
function Say([string]$m) { Add-Content -Path $Log -Value ((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') + ' ' + $m) }
Say "armed: waiting for CHAIN_NXT2_EXIT after $Stamp"
$waited = 0; $rc = ''
while ($true) {
  $rc = (& wsl.exe -d Ubuntu-24.04 bash "$Q/r2_exit_after_stamp.sh" $Stamp | Out-String).Trim()
  if ($rc -ne '') { break }
  if ($waited -ge $MaxWaitSeconds) { Say 'TIMEOUT; window NOT opened'; exit 8 }
  Start-Sleep -Seconds $PollSeconds; $waited += $PollSeconds
}
if ($rc -ne 'rc=0') { Say "R2 exited $rc; window NOT opened (coordinator decides)"; exit 9 }
Say 'R2 exit rc=0; waiting 180 s for the seal side to drain'; Start-Sleep -Seconds 180
& wsl.exe -d Ubuntu-24.04 bash "$Q/window_322_pre_shutdown.sh"
if ($LASTEXITCODE -ne 0) { Say "pre-shutdown step refused (rc=$LASTEXITCODE); window NOT opened"; exit 9 }
$cfg = Join-Path $env:USERPROFILE '.wslconfig'
Copy-Item $cfg ($cfg + '.bak-20261018-322') -Force
$text = Get-Content $cfg -Raw
if ($text -notmatch '(?m)^memory=44GB\s*$') {
  Say 'memory=44GB line not found; .wslconfig left unchanged, no shutdown; running the post-restart step directly so the GPU does not idle'
  & wsl.exe -d Ubuntu-24.04 bash "$Q/window_322_post_restart.sh"; Say "post step rc=$LASTEXITCODE"; exit $LASTEXITCODE
}
$text = $text -replace '(?m)^memory=44GB(\s*)$', ('memory=36GB$1' + "`r`n# 2026-10-18 owner ruling 322 A: 44 -> 36 GB (page-cache stalls under host compression); applied in the R2 rec2 seal window.")
[System.IO.File]::WriteAllText($cfg, $text, (New-Object System.Text.UTF8Encoding($false)))
Say '.wslconfig memory=36GB written (backup .wslconfig.bak-20261018-322); wsl --shutdown'
& wsl.exe --shutdown
Start-Sleep -Seconds 20
Say 'WSL shut down; post-restart step (it logs the new VM memory total)'
& wsl.exe -d Ubuntu-24.04 bash "$Q/window_322_post_restart.sh"
Say "post-restart step rc=$LASTEXITCODE (WSL log /home/chao/w322-window.out)"
exit $LASTEXITCODE
