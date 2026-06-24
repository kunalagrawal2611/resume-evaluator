# Start a single Resume Checker server (kills stale listeners on port 8000 first).
$ErrorActionPreference = "SilentlyContinue"
$port = 8000
$root = Split-Path -Parent $PSScriptRoot

netstat -ano | findstr ":$port.*LISTENING" | ForEach-Object {
    $procId = ($_ -split "\s+")[-1]
    if ($procId -match "^\d+$") { taskkill /F /PID $procId | Out-Null }
}
Start-Sleep -Seconds 2

Set-Location $root
Write-Host "Starting server at http://127.0.0.1:$port"
& "$root\.venv\Scripts\python.exe" -m uvicorn web_app:app --host 127.0.0.1 --port $port --reload
