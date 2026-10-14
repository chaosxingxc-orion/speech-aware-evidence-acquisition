# Attach the ext4 data VHD to WSL and mount it inside Ubuntu-24.04 whichever side starts first (owner decision 311, 2026-10-14).
# Registered as the Windows Scheduled Task SAEA-Mount-Data1 (triggers: at startup and at logon; highest privileges, because
# `wsl --mount` needs them -- the earlier logon-only, limited-rights task failed with 0xFFFFFFFF on the 2026-10-14 reboot and the
# distro then booted before the disk existed, so the fstab entry (`nofail`) was skipped and the data root was missing).
# Steps, each retried: 1. `wsl --mount --vhd <vhdx> --bare` (already attached counts as success); 2. `mount -a` as root inside the
# distro (idempotent); 3. verify the data root directory. Log: %LOCALAPPDATA%\saea-mount-data1.log. Exit 0 only when the root is visible.
param([string]$Vhd = 'E:\saea-data-1.vhdx', [string]$Distro = 'Ubuntu-24.04', [string]$Root = '/home/chao/saea-data/speechrl-data', [int]$Tries = 20, [int]$DelaySeconds = 15)
$log = Join-Path $env:LOCALAPPDATA 'saea-mount-data1.log'
function Log([string]$m) { $line = "{0:yyyy-MM-ddTHH:mm:ssZ} {1}" -f (Get-Date).ToUniversalTime(), $m; Add-Content -Path $log -Value $line; Write-Output $line }
Log "start vhd=$Vhd distro=$Distro"
for ($i = 1; $i -le $Tries; $i++) {
  $out = & wsl.exe --mount --vhd $Vhd --bare 2>&1 | Out-String
  $rc = $LASTEXITCODE
  $clean = ($out -replace '[\s\0]', '')   # wsl.exe prints UTF-16; strip NULs and spaces before matching
  if ($rc -eq 0 -or $clean -match 'ALREADY_ATTACHED|0x80040312|alreadyattached|alreadymounted') { Log "attach ok (try $i, rc=$rc)"; break }
  Log "attach failed (try $i, rc=$rc): $($out.Trim() -replace '\s+',' ')"
  if ($i -eq $Tries) { Log 'giving up on attach'; exit 2 }
  Start-Sleep -Seconds $DelaySeconds
}
for ($i = 1; $i -le $Tries; $i++) {
  & wsl.exe -d $Distro -u root -- mount -a 2>&1 | Out-Null
  $probe = & wsl.exe -d $Distro -- bash -c "test -d '$Root' && mountpoint -q /mnt/saea-data-1 && echo MOUNTED" 2>&1 | Out-String
  if ($probe -match 'MOUNTED') { Log "data root visible (try $i)"; exit 0 }
  Log "mount -a / probe not yet (try $i): $($probe.Trim() -replace '\s+',' ')"
  Start-Sleep -Seconds $DelaySeconds
}
Log 'giving up: data root not visible'; exit 3
