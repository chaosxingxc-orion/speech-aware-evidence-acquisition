param([Parameter(Mandatory=$true)][string]$ScriptPath,[Parameter(Mandatory=$true)][string]$Scratch)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Scratch){throw 'Use a fresh synthetic proof directory'}
$null=New-Item -ItemType Directory -Path $Scratch
$tokens=$null;$parseErrors=$null
$null=[Management.Automation.Language.Parser]::ParseFile($ScriptPath,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'PowerShell source does not parse'}
$encoding=New-Object Text.UTF8Encoding($false)
$results=@()
foreach($case in @('valid','draft','wrong-authority','missing','overlap','reordered','empty','duplicate','bad-plan-hash','bad-registration-hash')) {
 $reg=@{status='ROOT-ADMITTED';members=@(@{label='m0'},@{label='m1'},@{label='m2'},@{label='m3'})}
 $plan=@{status='ROOT-ADMITTED';authority='owner227';preserved_members=@('m0','m1');unstarted_members=@('m2','m3')}
 switch($case) {
  'draft' {$plan.status='DRAFT'}
  'wrong-authority' {$plan.authority='monitor'}
  'missing' {$plan.unstarted_members=@('m2')}
  'overlap' {$plan.unstarted_members=@('m1','m2','m3')}
  'reordered' {$plan.unstarted_members=@('m3','m2')}
  'empty' {$plan.preserved_members=@();$plan.unstarted_members=@('m0','m1','m2','m3')}
  'duplicate' {$reg.members[3].label='m2';$plan.unstarted_members=@('m2','m2')}
 }
 $rp=Join-Path $Scratch ($case+'-registration.json');$pp=Join-Path $Scratch ($case+'-plan.json')
 [IO.File]::WriteAllText($rp,($reg|ConvertTo-Json -Depth 6),$encoding)
 $rh=(Get-FileHash -LiteralPath $rp -Algorithm SHA256).Hash.ToLower();$plan.registration_sha256=$rh
 [IO.File]::WriteAllText($pp,($plan|ConvertTo-Json -Depth 6),$encoding)
 $ph=(Get-FileHash -LiteralPath $pp -Algorithm SHA256).Hash.ToLower()
 if($case -eq 'bad-plan-hash'){$ph='0'*64}
 if($case -eq 'bad-registration-hash'){$rh='0'*64}
 $out=Join-Path $Scratch ($case+'.stdout.log');$err=Join-Path $Scratch ($case+'.stderr.log')
 $proc=Start-Process powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$ScriptPath,'-RegistrationPath',$rp,'-RegistrationSHA',$rh,'-PlanPath',$pp,'-PlanSHA',$ph,'-ValidateOnly') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
 $expected=if($case -eq 'valid'){0}else{1}
 if($proc.ExitCode -ne $expected){throw ('Unexpected synthetic exit for '+$case)}
 if($case -eq 'valid') {
  $v=Get-Content -Raw -LiteralPath $out|ConvertFrom-Json
  if(($v.selected_members -join '|') -cne 'm2|m3' -or $v.model_contacts -ne 0){throw 'Synthetic selected members differ'}
 }
 $results+=@{case=$case;exit_code=$proc.ExitCode;passed=$true}
}
$receipt=@{schema='saea-suffix-owner-native-synthetic-proof-v1';at_utc=[DateTime]::UtcNow.ToString('o');source_sha256=(Get-FileHash -LiteralPath $ScriptPath -Algorithm SHA256).Hash.ToLower();passed=$true;cases=$results;model_contacts=0;scorer_contacts=0;scope='Native parser and pre-execution partition validation only; not full GPU dispatch proof'}
[IO.File]::WriteAllText((Join-Path $Scratch 'receipt.json'),($receipt|ConvertTo-Json -Depth 8),$encoding)
$receipt|ConvertTo-Json -Depth 8
