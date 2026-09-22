# Register (or replace) and start a Windows Scheduled Task that owns one long-lived WSL process
# (serving wrapper, monitor, or a campaign) independently of the Claude Code session.
# Battery and idle conditions disabled, no execution time limit, one instance at a time.
#   powershell -File saea_task.ps1 -Name SAEA-Campaign-B5e-rec -Script /mnt/c/.../b5erec_campaign.sh
#   powershell -File saea_task.ps1 -Name SAEA-Campaign-B5e-rec -Status
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Script = '',
  [switch]$Status,
  [switch]$Stop
)
if ($Status) {
  $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  if ($null -eq $t) { "$Name : (not registered)"; exit 0 }
  $i = Get-ScheduledTaskInfo -TaskName $Name
  "$Name : state=$($t.State) lastRun=$($i.LastRunTime) lastResult=$($i.LastTaskResult) stopOnBattery=$($t.Settings.StopIfGoingOnBatteries) limit=$($t.Settings.ExecutionTimeLimit)"
  exit 0
}
if ($Stop) { Stop-ScheduledTask -TaskName $Name; "$Name stopped"; exit 0 }
if ($Script -eq '') { throw 'Script is required to register' }
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DontStopOnIdleEnd -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddYears(1)
$action = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument ("-d Ubuntu-24.04 bash " + $Script)
Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $Name
Start-Sleep -Seconds 3
$t = Get-ScheduledTask -TaskName $Name
"$Name registered and started: state=$($t.State) stopOnBattery=$($t.Settings.StopIfGoingOnBatteries) limit=$($t.Settings.ExecutionTimeLimit)"
