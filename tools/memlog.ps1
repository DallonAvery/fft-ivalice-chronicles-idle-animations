# Record FFT: The Ivalice Chronicles memory use over time, for spotting leaks.
#
# Waits for FFT_enhanced.exe or FFT_classic.exe to start, then every $Interval seconds
# logs: process private memory, working set, handle count, and the process's GPU
# memory (dedicated = graphics card, shared = system RAM used by the GPU).
# Writes one CSV per game session into the project's diagnostics folder, named with the
# start time and the idle mod that Reloaded-II loaded (read from its newest log).
# Keeps going for further sessions until stopped.
#
# Usage: powershell -ExecutionPolicy Bypass -File memlog.ps1 [-Interval 5]
param([int]$Interval = 5)

$outDir = Join-Path (Split-Path $PSScriptRoot -Parent) "diagnostics"
New-Item -ItemType Directory -Force $outDir | Out-Null
$logDir = Join-Path $env:APPDATA "Reloaded-Mod-Loader-II\Logs"

function Get-ModLabel {
    $log = Get-ChildItem $logDir -File -Filter "*FFT_*.txt" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $log) { return "unknown" }
    $mods = Get-Content $log.FullName | Select-String '\[Reloaded\] Loading: (.+)$' |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Where-Object { $_ -notmatch 'Shared Lib|Sigscan|Mod Loader' }
    if ($mods) { return ($mods -join "+") } else { return "no idle mod" }
}

while ($true) {
    $p = $null
    while (-not $p) {
        $p = Get-Process -Name FFT_enhanced, FFT_classic -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $p) { Start-Sleep -Seconds 2 }
    }
    Start-Sleep -Seconds 4   # let Reloaded-II write its log
    $label = (Get-ModLabel) -replace '[^\w\-\(\)\+ ]', '' -replace ' ', '_'
    $file = Join-Path $outDir ("mem_{0}_{1}_{2}.csv" -f (Get-Date -Format "yyyyMMdd_HHmmss"), $p.ProcessName, $label)
    "time,seconds,private_mb,workingset_mb,handles,gpu_dedicated_mb,gpu_shared_mb" | Set-Content $file -Encoding utf8
    $t0 = Get-Date
    Write-Output "recording $($p.ProcessName) (pid $($p.Id)) -> $file"
    while (-not $p.HasExited) {
        $p.Refresh()
        $ded = 0; $sh = 0
        try {
            $c = Get-Counter "\GPU Process Memory(pid_$($p.Id)_*)\Dedicated Usage", "\GPU Process Memory(pid_$($p.Id)_*)\Shared Usage" -ErrorAction Stop
            foreach ($s in $c.CounterSamples) {
                if ($s.Path -match 'dedicated usage') { $ded += $s.CookedValue } else { $sh += $s.CookedValue }
            }
        } catch {}
        "{0},{1},{2},{3},{4},{5},{6}" -f (Get-Date -Format "HH:mm:ss"), [int]((Get-Date) - $t0).TotalSeconds,
            [math]::Round($p.PrivateMemorySize64 / 1MB), [math]::Round($p.WorkingSet64 / 1MB), $p.HandleCount,
            [math]::Round($ded / 1MB), [math]::Round($sh / 1MB) | Add-Content $file -Encoding utf8
        Start-Sleep -Seconds $Interval
    }
    Write-Output "session ended after $([int]((Get-Date) - $t0).TotalSeconds) s"
}
