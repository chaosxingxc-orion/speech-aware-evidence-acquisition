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
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Script = '',
  [switch]$Status,
  [switch]$Stop,
  [switch]$Start
)
function Register-SaeaTask([string]$TaskName, [string]$TaskScript, [bool]$Strict) {
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DontStopOnIdleEnd -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddYears(1)
  $action = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument ("-d Ubuntu-24.04 bash " + $TaskScript)
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
  if ($Script -ne '') { $wanted = "-d Ubuntu-24.04 bash " + $Script }
  $current = $null
  if ($null -ne $t) { $current = ($t.Actions | Select-Object -First 1).Arguments }
  if ($null -eq $t -or ($null -ne $wanted -and $current -ne $wanted)) {
    if ($null -eq $wanted) { "$Name : not registered and no -Script given"; exit 3 }
    try {
      Register-SaeaTask $Name $Script $true
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
Register-SaeaTask $Name $Script $false
Start-ScheduledTask -TaskName $Name
Start-Sleep -Seconds 3
$t = Get-ScheduledTask -TaskName $Name
"$Name registered and started: state=$($t.State) stopOnBattery=$($t.Settings.StopIfGoingOnBatteries) limit=$($t.Settings.ExecutionTimeLimit)"
