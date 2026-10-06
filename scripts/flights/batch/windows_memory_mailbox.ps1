# Sample Windows physical memory only after a fresh job-bound request.
param(
    [Parameter(Mandatory=$true)][string]$Directory,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')][string]$Session,
    [ValidateRange(15,600)][int]$IdleSeconds=60
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($Directory)
$encoding=New-Object System.Text.UTF8Encoding($false)
function Publish([string]$name,$value) {
    $target=Join-Path $root $name
    $temporary=$target+'.tmp'
    $bytes=$encoding.GetBytes(($value | ConvertTo-Json -Compress))
    $file=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $file.Write($bytes,0,$bytes.Length); $file.Flush($true) } finally { $file.Dispose() }
    [IO.File]::Move($temporary,$target)
}
function ReadRecord([string]$path) {
    if ((Get-Item -LiteralPath $path).Length -gt 4096) { throw 'Oversized request' }
    return (ConvertFrom-Json ([IO.File]::ReadAllText($path)))
}
$exitCode=1
try {
    if (-not [IO.Directory]::Exists($root)) { throw 'Missing private mailbox directory' }
    Add-Type -AssemblyName Microsoft.VisualBasic
    $info=New-Object Microsoft.VisualBasic.Devices.ComputerInfo
    Publish 'ready.json' ([ordered]@{session=$Session;observer_pid=$PID;started_at=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()})
    $sequence=1
    $idle=[Diagnostics.Stopwatch]::StartNew()
    while ($true) {
        $stop=Join-Path $root 'STOP.json'
        if ([IO.File]::Exists($stop)) {
            if ((ReadRecord $stop).session -cne $Session) { throw 'STOP session mismatch' }
            $exitCode=0;break
        }
        if ($idle.Elapsed.TotalSeconds -ge $IdleSeconds) { throw 'Mailbox idle deadline' }
        $request=Join-Path $root ('request-{0:D8}.json' -f $sequence)
        if (-not [IO.File]::Exists($request)) { Start-Sleep -Milliseconds 20;continue }
        $q=ReadRecord $request
        if ($q.session -cne $Session -or $q.sequence -isnot [int] -or $q.sequence -ne $sequence -or $q.nonce -cnotmatch '^[0-9a-f]{32}$') { throw 'Request identity mismatch' }
        $watch=[Diagnostics.Stopwatch]::StartNew()
        $free=$info.AvailablePhysicalMemory
        $total=$info.TotalPhysicalMemory
        $watch.Stop()
        Publish ('response-{0:D8}.json' -f $sequence) ([ordered]@{
            session=$Session;nonce=$q.nonce;sequence=$sequence;observer_pid=$PID;
            sampled_at=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();
            sample_elapsed_ms=$watch.Elapsed.TotalMilliseconds;available_bytes=$free;total_bytes=$total
        })
        $sequence++;$idle.Restart()
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
} finally {
    Publish 'finished.json' ([ordered]@{session=$Session;observer_pid=$PID;exit_code=$exitCode;at=[DateTimeOffset]::UtcNow.ToString('o')})
}
exit $exitCode
