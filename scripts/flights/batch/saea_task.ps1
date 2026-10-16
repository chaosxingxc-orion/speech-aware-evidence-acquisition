# Register (or replace) and start a Windows Scheduled Task that owns one long-lived WSL process
# (serving wrapper, monitor, or a campaign) independently of the Claude Code session.
# Battery and idle conditions disabled, no execution time limit, one instance at a time.
#   powershell -File saea_task.ps1 -Name SAEA-Campaign-B5e-rec -Script /mnt/c/.../b5erec_campaign.sh
#   powershell -File saea_task.ps1 -Name SAEA-Campaign-B5e-rec -Status
#   powershell -File saea_task.ps1 -Name SAEA-Serving -Script /mnt/d/.../serving_task_entry.sh -Start
# -Start (owner decision 163, used by serving_swap.sh) starts an already-registered task WITHOUT re-registering
# it when its action already runs -Script: from a WSL interop shell Register-ScheduledTask is refused with
# 0x80070005 for a task registered from an elevated session (queue log of 2026-09-27), while Start-ScheduledTask
# is not. It registers only a missing task or one whose action differs, and fails with a non-zero exit (3 register
# refused, 4 start refused, 5 not running afterwards) instead of printing an error and carrying on.
# -RepeatMinutes N (owner decision 182, added for the idle watchdog: every task this script registered before
# used a one-shot "-Once -At +1 year" trigger and was started by hand or by -Start -- there was no repetition at
# all). N > 0 registers a real recurring trigger instead (fires every N minutes, indefinitely); N = 0 (the
# default) keeps the old one-shot-until-started trigger, so every existing caller is unaffected.
#   powershell -File saea_task.ps1 -Name SAEA-Watchdog -Script /mnt/d/.../idle_watchdog.sh -RepeatMinutes 5
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Script = '',
  [switch]$Status,
  [switch]$Stop,
  [switch]$Start,
  [int]$RepeatMinutes = 0,
  [string]$WslUser = ''   # 2026-10-16: run the script as this distro user (e.g. root for /proc/sys writes); empty = the default user
)
function Register-SaeaTask([string]$TaskName, [string]$TaskScript, [bool]$Strict, [int]$Repeat) {
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DontStopOnIdleEnd -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -Hidden
  if ($Repeat -gt 0) {
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Repeat)
  } else {
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddYears(1)
  }
  # Hidden console (owner 2026-10-12: every task launch used to open a visible console window and leaked a conhost; the
  # watchdog alone spawned one every five minutes). wsl.exe inherits the hidden PowerShell console, so no window appears.
  $userArg = if ($script:WslUser -ne '') { " -u " + $script:WslUser } else { '' }
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ("-NoProfile -NonInteractive -WindowStyle Hidden -Command `"& wsl.exe -d Ubuntu-24.04" + $userArg + " bash " + $TaskScript + "`"")
  if ($Strict) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force -ErrorAction Stop | Out-Null
  } else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
  }
}
if ($Status) {
  $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  if ($null -eq $t) { "$Name : (not registered)"; exit 0 }
  $i = Get-ScheduledTaskInfo -TaskName $Name
  "$Name : state=$($t.State) lastRun=$($i.LastRunTime) lastResult=$($i.LastTaskResult) stopOnBattery=$($t.Settings.StopIfGoingOnBatteries) limit=$($t.Settings.ExecutionTimeLimit) action=$(($t.Actions | Select-Object -First 1).Arguments)"
  exit 0
}
if ($Stop) { Stop-ScheduledTask -TaskName $Name; "$Name stopped"; exit 0 }
if ($Start) {
  $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  $wanted = $null
  if ($Script -ne '') { $wanted = "-d Ubuntu-24.04" + $(if ($WslUser -ne '') { " -u " + $WslUser } else { '' }) + " bash " + $Script }
  $current = $null
  if ($null -ne $t) { $current = ($t.Actions | Select-Object -First 1).Arguments }
  if ($null -eq $t -or ($null -ne $wanted -and $current -ne $wanted)) {
    if ($null -eq $wanted) { "$Name : not registered and no -Script given"; exit 3 }
    try {
      Register-SaeaTask $Name $Script $true $RepeatMinutes
      "$Name : registered action '$wanted' (was '$current')"
    } catch {
      "$Name : register refused: $($_.Exception.Message)"
      exit 3
    }
    $t = Get-ScheduledTask -TaskName $Name
  }
  if ($t.State -eq 'Running') { "$Name : already running (action '$(($t.Actions | Select-Object -First 1).Arguments)')"; exit 0 }
  try { Start-ScheduledTask -TaskName $Name -ErrorAction Stop } catch { "$Name : start refused: $($_.Exception.Message)"; exit 4 }
  Start-Sleep -Seconds 3
  $t = Get-ScheduledTask -TaskName $Name
  "$Name started: state=$($t.State) action='$(($t.Actions | Select-Object -First 1).Arguments)'"
  if ($t.State -ne 'Running') { exit 5 }
  exit 0
}
if ($Script -eq '') { throw 'Script is required to register' }
Register-SaeaTask $Name $Script $false $RepeatMinutes
Start-ScheduledTask -TaskName $Name
Start-Sleep -Seconds 3
$t = Get-ScheduledTask -TaskName $Name
"$Name registered and started: state=$($t.State) stopOnBattery=$($t.Settings.StopIfGoingOnBatteries) limit=$($t.Settings.ExecutionTimeLimit)"
