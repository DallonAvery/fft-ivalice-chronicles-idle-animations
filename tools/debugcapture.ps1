# Capture Windows debug messages (OutputDebugString) to a file, like Sysinternals DebugView.
#
# The Direct3D 12 debug layer reports problems this way ("D3D12 ERROR: ..."), so with
# the debug layer forced on for the game, this records why a graphics call was invalid.
# Messages from every process in this Windows session are recorded with time, process
# id and name; lines from the game (FFT_*) are marked with "<<".
#
# Output: <project>\diagnostics\debug_<start time>.log   (runs until stopped)
# Usage: powershell -ExecutionPolicy Bypass -File debugcapture.ps1
$outDir = Join-Path (Split-Path $PSScriptRoot -Parent) "diagnostics"
New-Item -ItemType Directory -Force $outDir | Out-Null
$out = Join-Path $outDir ("debug_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

Add-Type -TypeDefinition @"
using System;
using System.IO;
using System.Text;
using System.Threading;
using System.IO.MemoryMappedFiles;
using System.Diagnostics;
using System.Collections.Generic;

public static class DbWin {
    public static void Run(string path) {
        bool created;
        using (var mutex = new Mutex(false, "DBWinMutex", out created))
        using (var bufferReady = new EventWaitHandle(false, EventResetMode.AutoReset, "DBWIN_BUFFER_READY"))
        using (var dataReady = new EventWaitHandle(false, EventResetMode.AutoReset, "DBWIN_DATA_READY"))
        using (var map = MemoryMappedFile.CreateOrOpen("DBWIN_BUFFER", 4096))
        using (var view = map.CreateViewAccessor(0, 4096))
        using (var log = new StreamWriter(path, true, new UTF8Encoding(false))) {
            log.AutoFlush = true;
            log.WriteLine("# debug capture started " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            var names = new Dictionary<int, string>();
            var bytes = new byte[4092];
            long skipped = 0;
            while (true) {
                bufferReady.Set();
                if (!dataReady.WaitOne(1000)) continue;
                int pid = view.ReadInt32(0);
                view.ReadArray(4, bytes, 0, bytes.Length);
                int len = Array.IndexOf(bytes, (byte)0);
                if (len < 0) len = bytes.Length;
                string msg = Encoding.Default.GetString(bytes, 0, len).TrimEnd('\r', '\n');
                string name;
                if (!names.TryGetValue(pid, out name)) {
                    try { name = Process.GetProcessById(pid).ProcessName; } catch { name = "?"; }
                    names[pid] = name;
                }
                bool game = name.StartsWith("FFT_", StringComparison.OrdinalIgnoreCase);
                // The game repeats two harmless warnings thousands of times a minute; count them only.
                if (game && (msg.Contains("WARNING #820:") || msg.Contains("WARNING #1424:"))) {
                    skipped++;
                    if (skipped % 100000 == 0)
                        log.WriteLine(string.Format("{0} [{1} {2}] << (skipped {3} repeated warnings #820/#1424 so far)",
                            DateTime.Now.ToString("HH:mm:ss.fff"), pid, name, skipped));
                    continue;
                }
                log.WriteLine(string.Format("{0} [{1} {2}]{3} {4}", DateTime.Now.ToString("HH:mm:ss.fff"),
                    pid, name, game ? " <<" : "", msg));
            }
        }
    }
}
"@
Write-Output "capturing debug messages -> $out"
[DbWin]::Run($out)
