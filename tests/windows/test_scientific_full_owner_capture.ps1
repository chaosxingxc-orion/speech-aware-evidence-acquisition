param([Parameter(Mandatory=$true)][string]$CapturePath,[Parameter(Mandatory=$true)][string]$EvidenceRoot)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1')
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Management/Microsoft.PowerShell.Management.psd1')
if (Test-Path -LiteralPath $EvidenceRoot) { throw 'Preserve prior proof directory' }
$null=New-Item -ItemType Directory -Path $EvidenceRoot
if (-not (Test-Path -LiteralPath $CapturePath)) { throw 'Capture entry is missing' }
$encoding=New-Object Text.UTF8Encoding($false)
$sha='1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
$cases=@()
foreach ($code in @(0,23)) {
 $root=Join-Path $EvidenceRoot ('case with spaces '+$code)
 $null=New-Item -ItemType Directory -Path $root
 $child=Join-Path $root 'synthetic owner.ps1'
 $script='param([string]$RegistrationSHA)' + "`r`n" + 'if ($RegistrationSHA -cne '''+$sha+''') { exit 52 }' + "`r`n" + '[Console]::Out.WriteLine(''synthetic stdout'');[Console]::Error.WriteLine(''synthetic stderr'')' + "`r`n" + '[Environment]::Exit('+$code+')'
 [IO.File]::WriteAllText($child,$script,$encoding)
 $vbs=Join-Path $root 'hidden.vbs'
 $command='cmd.exe /d /c ""'+$CapturePath+'" "'+$child+'" "'+$sha+'" "'+$root+'""'
 [IO.File]::WriteAllText($vbs,'Set sh=CreateObject("WScript.Shell")'+"`r`n"+'WScript.Quit sh.Run("'+$command.Replace('"','""')+'",0,True)'+"`r`n",$encoding)
 $proc=Start-Process wscript.exe -ArgumentList @('//B','//Nologo',('"'+$vbs+'"')) -WindowStyle Hidden -PassThru
 $null=$proc.Handle;$proc.WaitForExit();$proc.Refresh()
 if ($proc.ExitCode -ne $code) { throw 'Hidden supervisor lost native exit' }
 $receipt=Get-Content -Raw -LiteralPath (Join-Path $root 'owner-process-exit.json')|ConvertFrom-Json
 if ($receipt.schema -cne 'saea-scientific-owner-native-exit-v1' -or $receipt.exit_code -ne $code -or $receipt.registration_sha256 -cne $sha) { throw 'Exit binding differs' }
 if ((Get-Content -Raw (Join-Path $root 'owner.stdout.log')).Trim() -cne 'synthetic stdout') { throw 'stdout capture differs' }
 if ((Get-Content -Raw (Join-Path $root 'owner.stderr.log')).Trim() -cne 'synthetic stderr') { throw 'stderr capture differs' }
 $before=@('owner-process-exit.json','owner.stdout.log','owner.stderr.log')|ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $root $_) -Algorithm SHA256).Hash }
 $proc=Start-Process wscript.exe -ArgumentList @('//B','//Nologo',('"'+$vbs+'"')) -WindowStyle Hidden -PassThru
 $null=$proc.Handle;$proc.WaitForExit();$proc.Refresh()
 if ($proc.ExitCode -ne 91) { throw 'Repeated launch was not refused' }
 $after=@('owner-process-exit.json','owner.stdout.log','owner.stderr.log')|ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $root $_) -Algorithm SHA256).Hash }
 if (($before -join '|') -cne ($after -join '|')) { throw 'Repeated launch changed preserved evidence' }
 $cases+=@{native_exit=$code;propagated=$true;streams_preserved=$true;repeat_refused=$true}
}
foreach ($name in @('owner.stdout.log','owner.stderr.log')) {
 $root=Join-Path $EvidenceRoot ('preserved '+$name)
 $null=New-Item -ItemType Directory -Path $root
 [IO.File]::WriteAllText((Join-Path $root $name),'preserved evidence',$encoding)
 $before=(Get-FileHash -LiteralPath (Join-Path $root $name) -Algorithm SHA256).Hash
 $vbs=Join-Path $root 'hidden.vbs'
 $command='cmd.exe /d /c ""'+$CapturePath+'" "'+(Join-Path $root 'absent-owner.ps1')+'" "'+$sha+'" "'+$root+'""'
 [IO.File]::WriteAllText($vbs,'Set sh=CreateObject("WScript.Shell")'+"`r`n"+'WScript.Quit sh.Run("'+$command.Replace('"','""')+'",0,True)'+"`r`n",$encoding)
 $proc=Start-Process wscript.exe -ArgumentList @('//B','//Nologo',('"'+$vbs+'"')) -WindowStyle Hidden -PassThru
 $null=$proc.Handle;$proc.WaitForExit();$proc.Refresh()
 if ($proc.ExitCode -ne 91 -or (Test-Path (Join-Path $root 'owner-process-exit.json'))) { throw 'Existing stream did not refuse prelaunch' }
 if ((Get-FileHash -LiteralPath (Join-Path $root $name) -Algorithm SHA256).Hash -cne $before) { throw 'Prior stream changed' }
 $cases+=@{preserved_stream=$name;refused_before_child=$true}
}
$result=@{schema='saea-scientific-full-owner-capture-proof-v1';at_utc=[DateTimeOffset]::UtcNow.ToString('o');cases=$cases;capture_sha256=(Get-FileHash -LiteralPath $CapturePath -Algorithm SHA256).Hash.ToLower();model_contacts=0;scorer_contacts=0}
[IO.File]::WriteAllText((Join-Path $EvidenceRoot 'receipt.json'),($result|ConvertTo-Json -Depth 8),$encoding)
$result|ConvertTo-Json -Depth 8
