param([Parameter(Mandatory=$true)][string]$PlanPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1')
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Management/Microsoft.PowerShell.Management.psd1')
Import-Module (Join-Path $PSHOME 'Modules/CimCmdlets/CimCmdlets.psd1')
Import-Module (Join-Path $PSHOME 'Modules/ScheduledTasks/ScheduledTasks.psd1')
$plan=Get-Content -Raw -LiteralPath $PlanPath|ConvertFrom-Json
$task=Get-ScheduledTask -TaskName $plan.original_task_name
$info=Get-ScheduledTaskInfo -TaskName $plan.original_task_name
$all=@(Get-CimInstance Win32_Process)
$ancestors=[Collections.Generic.HashSet[int]]::new();$nextPid=$PID
while($nextPid -and $ancestors.Add([int]$nextPid)) {
 $item=$all|Where-Object ProcessId -eq $nextPid|Select-Object -First 1
 if(-not $item){break};$nextPid=$item.ParentProcessId
}
$bound=@($all|Where-Object {(-not $ancestors.Contains([int]$_.ProcessId)) -and $_.CommandLine -like ('*'+$plan.original_windows_root+'*')}|ForEach-Object {@{pid=$_.ProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString('o');command=$_.CommandLine}})
$owner=@($all|Where-Object {$_.ProcessId -eq $plan.original_owner_pid -and $_.CreationDate.ToUniversalTime() -eq [DateTime]::Parse($plan.original_owner_created_utc).ToUniversalTime()})
$record=@{schema='saea-original-owner-native-observation-v1';observed_at=[DateTime]::UtcNow.ToString('o');task_name=$task.TaskName;task_state=[string]$task.State;task_result=$info.LastTaskResult;original_owner_live=($owner.Count -gt 0);bound_windows_processes=$bound;registration_sha256=$plan.registration_sha256}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 8))
$stream=[IO.File]::Open($OutputPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
if($bound.Count -ne 0 -or $owner.Count -ne 0 -or $task.State -ne 'Ready' -or $info.LastTaskResult -ne $plan.original_task_result){throw 'Original native owner has not settled as admitted'}
