param(
 [Parameter(Mandatory=$true)][string]$RegistrationPath,
 [Parameter(Mandatory=$true)][string]$RegistrationSHA,
 [Parameter(Mandatory=$true)][string]$PlanPath,
 [Parameter(Mandatory=$true)][string]$PlanSHA,
 [switch]$ValidateOnly
)
$ErrorActionPreference='Stop'
# Resolve native Windows modules independently of the invoking shell's module path.
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1')
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Management/Microsoft.PowerShell.Management.psd1')
if ((Get-FileHash -LiteralPath $PlanPath -Algorithm SHA256).Hash.ToLower() -cne $PlanSHA) { throw 'Continuation plan hash differs' }
$plan=Get-Content -Raw -LiteralPath $PlanPath | ConvertFrom-Json
if ($plan.status -cne 'ROOT-ADMITTED' -or $plan.authority -cne 'owner227') { throw 'Continuation admission absent' }
if ($plan.registration_sha256 -cne $RegistrationSHA) { throw 'Registration binding differs' }
if ((Get-FileHash -LiteralPath $RegistrationPath -Algorithm SHA256).Hash.ToLower() -cne $RegistrationSHA) { throw 'Registration hash differs' }
$reg=Get-Content -Raw -LiteralPath $RegistrationPath | ConvertFrom-Json
if ($reg.status -cne 'ROOT-ADMITTED') { throw 'Original admission absent' }
$labels=@($reg.members | ForEach-Object {$_.label})
$expected=@($plan.preserved_members)+@($plan.unstarted_members)
if ($plan.preserved_members.Count -eq 0 -or $plan.unstarted_members.Count -eq 0 -or
    $labels.Count -ne $expected.Count -or ($labels -join '|') -cne ($expected -join '|') -or
    @($labels | Select-Object -Unique).Count -ne $labels.Count) { throw 'Exact continuation partition differs' }
$selected=@($reg.members | Where-Object {$_.label -cin $plan.unstarted_members})
if ($ValidateOnly) {
 @{status='PARTITION_SYNTAX_VERIFIED_NOT_RUNTIME_ADMISSION';selected_members=@($selected|ForEach-Object {$_.label});model_contacts=0} | ConvertTo-Json -Compress
 exit 0
}
$entryRoot=$plan.windows_receipt_root
$originalRoot=$plan.original_windows_root
$linuxRoot=$plan.original_linux_root
$registrationPath=$RegistrationPath
if ($entryRoot -ceq $originalRoot) { throw 'Continuation must preserve the original root receipts' }
foreach ($source in $plan.windows_pinned_files) {
 if ((Get-FileHash -LiteralPath $source.path -Algorithm SHA256).Hash.ToLower() -cne $source.sha256) { throw 'Pinned continuation source differs' }
}
# This preflight verifies immutable pins, fresh native identities and every untouched member.
& $plan.windows_original_observer -PlanPath $PlanPath -OutputPath $plan.windows_native_observation_path
& wsl.exe -d Ubuntu-24.04 -- env PYTHONDONTWRITEBYTECODE=1 /home/chao/.venvs/speechrl/bin/python -B $plan.linux_preflight --plan $plan.linux_plan --sha256 $PlanSHA
if ($LASTEXITCODE -ne 0) { throw 'Continuation preflight refused before contacts' }
$encoding=New-Object Text.UTF8Encoding($false)
function WriteEvidence([string]$name,$value,[string]$root=$entryRoot) {
 $path=Join-Path $root $name
 $bytes=$encoding.GetBytes(($value | ConvertTo-Json -Depth 12))
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try { $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true) } finally { $stream.Dispose() }
}
$exitCode=1;$results=@();$failure=$null
try {
 if ((Get-FileHash -LiteralPath $registrationPath -Algorithm SHA256).Hash.ToLower() -cne $RegistrationSHA) { throw 'Registration hash differs' }
 $reg=Get-Content -Raw -LiteralPath $registrationPath | ConvertFrom-Json
 if ($reg.status -cne 'ROOT-ADMITTED') { throw 'Root admission absent' }
 if ((Get-FileHash -LiteralPath (Join-Path $originalRoot 'broker.ps1') -Algorithm SHA256).Hash.ToLower() -cne $reg.observer_implementation.windows_broker.sha256) { throw 'Observer source differs' }
 WriteEvidence 'scientific-started.json' @{at_utc=[DateTimeOffset]::UtcNow.ToString('o');windows_owner_pid=$PID;registration_sha256=$RegistrationSHA;worker=$reg.worker;worker_commit=$reg.worker_commit;official_score_jobs_expected=$selected.Count;continuation_plan_sha256=$PlanSHA}
 foreach ($member in $selected) {
  $label=$member.label;$unit=Join-Path $originalRoot $label
  if (Test-Path -LiteralPath $unit) { throw 'Member directory already exists' }
  $mailbox=Join-Path $unit 'mailbox'
  $null=New-Item -ItemType Directory -Path $mailbox
  $broker=Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $originalRoot 'broker.ps1'),'-Directory',$mailbox,'-Session',$label,'-IdleSeconds','120') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $unit 'observer.stdout.log') -RedirectStandardError (Join-Path $unit 'observer.stderr.log')
  $null=$broker.Handle
  try {
   $readyPath=Join-Path $mailbox 'ready.json';$deadline=[DateTime]::UtcNow.AddSeconds(10)
   while (-not (Test-Path -LiteralPath $readyPath)) {
    if ($broker.HasExited -or [DateTime]::UtcNow -gt $deadline) { throw 'Owned observer failed readiness' }
    Start-Sleep -Milliseconds 30
   }
   $ready=Get-Content -Raw -LiteralPath $readyPath | ConvertFrom-Json
   if ($ready.observer_pid -ne $broker.Id -or $ready.session -cne $label) { throw 'Observer identity mismatch' }
   WriteEvidence ($label+'/windows-observer-binding.json') @{session=$label;observer_pid=$broker.Id;observer_start_time=$broker.StartTime.ToUniversalTime().ToString('o');registration_sha256=$RegistrationSHA} $originalRoot
   $arguments=@('-d','Ubuntu-24.04','--cd',$reg.worker,'--','env','PYTHONDONTWRITEBYTECODE=1',('PYTHONPATH='+$reg.worker+'/src'),'/home/chao/.venvs/speechrl/bin/python','-B',($linuxRoot+'/launch-member-v1.py'),'--registration',($linuxRoot+'/registration-v1.json'),'--sha256',$RegistrationSHA,'--label',$label)
   $child=Start-Process wsl.exe -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $unit 'windows-child.stdout.log') -RedirectStandardError (Join-Path $unit 'windows-child.stderr.log')
   $null=$child.Handle
   # Sample freshness is bounded inside the original running-worker guard.
   $child.WaitForExit();$child.Refresh();$code=$child.ExitCode
   if ($null -eq $code) { throw 'Missing owned WSL exit code' }
   WriteEvidence ($label+'-wsl-process-exit.json') @{exit_code=$code;pid=$child.Id;at_utc=[DateTimeOffset]::UtcNow.ToString('o')} $originalRoot
   if (-not $broker.WaitForExit(10000)) { throw 'Observer did not close after its child' }
   $broker.Refresh()
   $item=@{label=$label;run_id=$member.run_id;attempt_id=$member.attempt_id;exit_code=$code;observer_exit_code=$broker.ExitCode;at_utc=[DateTimeOffset]::UtcNow.ToString('o')}
   $results+=$item;WriteEvidence ($label+'-windows-exit.json') $item $originalRoot
   if ($code -ne 0 -or $broker.ExitCode -ne 0) { throw 'Member failed; stop without retry' }
  } finally {
   if (-not $broker.HasExited) { $broker.Kill();$broker.WaitForExit() }
  }
 }
 $exitCode=0
} catch {
 $failure=@{type=$_.Exception.GetType().Name;message=$_.Exception.Message;at_utc=[DateTimeOffset]::UtcNow.ToString('o')}
 WriteEvidence 'scientific-windows-failure.json' $failure
} finally {
 WriteEvidence 'scientific-finished.json' @{at_utc=[DateTimeOffset]::UtcNow.ToString('o');exit_code=$exitCode;members=$results;failure=$failure;official_score_jobs_expected=$selected.Count;registration_sha256=$RegistrationSHA;continuation_plan_sha256=$PlanSHA}
}
exit $exitCode
