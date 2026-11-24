[CmdletBinding()]
param(
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Start',
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
$localEnvironment = Join-Path $runtimeDir 'environment.ps1'
if (Test-Path -LiteralPath $localEnvironment) { . $localEnvironment }
$stateFile = Join-Path $runtimeDir 'services.json'
$state = @{}
if (Test-Path -LiteralPath $stateFile) {
    $saved = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    foreach ($entry in $saved.PSObject.Properties) { $state[$entry.Name] = $entry.Value }
}

function Save-State {
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $stateFile -Encoding UTF8
}

function Test-Docker {
    $command = Get-Command docker.exe -ErrorAction SilentlyContinue
    if (-not $command) { return $false }
    # A partially started Desktop engine can leave docker info waiting for minutes.
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = $command.Source
    $process.StartInfo.Arguments = 'info --format "{{.ServerVersion}}"'
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    try {
        $process.Start() | Out-Null
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(10000)) {
            $process.Kill()
            return $false
        }
        return ($process.ExitCode -eq 0)
    } catch { return $false }
    finally { $process.Dispose() }
}

function Get-Listener([int]$Port) {
    return @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Test-Service([string]$Name) {
    try {
        if ($Name -eq 'backend') {
            $schema = Invoke-RestMethod 'http://127.0.0.1:10001/openapi.json' -TimeoutSec 3
            return ($schema.info.title -eq 'Skyper Agent Workspace')
        }
        $page = Invoke-WebRequest 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 3
        return ($page.StatusCode -eq 200 -and $page.Content -match '<title>Skyper')
    } catch { return $false }
}

function Find-Python {
    $candidates = @((Join-Path $projectRoot 'Skyper-python\.venv\Scripts\python.exe'))
    if ($env:CONDA_PREFIX) { $candidates += Join-Path $env:CONDA_PREFIX 'python.exe' }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        $ErrorActionPreference = 'Continue'
        & $candidate -c 'import uvicorn, fastapi, sqlalchemy, asyncpg, langgraph, bcrypt' 1>$null 2>$null
        $ready = $LASTEXITCODE -eq 0
        $ErrorActionPreference = 'Stop'
        if ($ready) { return $candidate }
    }
    throw 'No ready Python environment found. See STARTUP.md for installing requirements.txt.'
}

function Start-ServiceProcess([string]$Name, [int]$Port, [string]$Executable, [string]$Arguments, [string]$Directory) {
    if (Test-Service $Name) {
        Write-Host "[OK] $Name is already ready on port $Port."
        return
    }
    if ((Get-Listener $Port).Count -gt 0) {
        throw "Port $Port is occupied by an unready or different application. Check its process before restarting."
    }
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $Directory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir "$Name.stdout.log") -RedirectStandardError (Join-Path $runtimeDir "$Name.stderr.log") -PassThru
    $state[$Name] = @{
        id = $process.Id
        startedUtc = $process.StartTime.ToUniversalTime().ToString('o')
        executable = $Executable
    }
    Save-State
    $deadline = (Get-Date).AddSeconds(120)
    do {
        if (Test-Service $Name) {
            Write-Host "[OK] $Name is ready on port $Port."
            return
        }
        $process.Refresh()
        if ($process.HasExited) { throw "$Name exited. Check .runtime/$Name.stderr.log." }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "$Name did not become ready within 120 seconds. Check .runtime/$Name.stderr.log."
}

Push-Location $projectRoot
try {
    if ($Action -eq 'Status') {
        foreach ($name in @('backend', 'frontend')) {
            Write-Host ("{0}: {1}" -f $name, (Test-Service $name))
        }
        if (Test-Docker) { & docker compose ps }
        else { Write-Host 'Docker Desktop is not ready.' }
        exit 0
    }

    if ($Action -eq 'Stop') {
        foreach ($name in @('frontend', 'backend')) {
            if (-not $state.ContainsKey($name)) { continue }
            $record = $state[$name]
            $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
            if ($process) {
                $sameStart = $process.StartTime.ToUniversalTime().ToString('o') -eq $record.startedUtc
                if (-not ($sameStart -and $process.Path -eq $record.executable)) {
                    throw "PID for $name belongs to another process; nothing was stopped."
                }
                # Windows venv python.exe launches the actual interpreter as a
                # child. Stop this verified process tree so its port is released.
                & taskkill.exe /PID $process.Id /T /F | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "Could not stop $name process tree." }
                $process.WaitForExit(10000) | Out-Null
                Write-Host "[OK] $name stopped."
            }
            $state.Remove($name)
            Save-State
        }
        if ((Get-Listener 10001).Count -gt 0 -or (Get-Listener 5173).Count -gt 0) {
            throw 'An application started outside this launcher is still running. Stop its own terminal first.'
        }
        if (Test-Docker) {
            & docker compose stop
            if ($LASTEXITCODE -ne 0) { throw 'Could not stop the Docker services.' }
        }
        Write-Host '[OK] Skyper stopped. Containers and data volumes are retained.'
        exit 0
    }

    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'Skyper-python\.env'))) {
        throw 'Skyper-python/.env is missing. Copy .env.example and configure it as described in STARTUP.md.'
    }
    $node = Get-Command node.exe -ErrorAction Stop
    $vite = Join-Path $projectRoot 'Skyper-frontend\node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $vite)) { throw 'Frontend dependencies missing. Run npm ci in Skyper-frontend.' }
    $python = Find-Python
    Write-Host "[1/3] Preparing Docker services. Python: $python"
    Get-Command docker -ErrorAction Stop | Out-Null
    if (-not (Test-Docker)) {
        $desktop = $env:SKYPER_DOCKER_DESKTOP
        if (-not $desktop) { $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe' }
        if (-not (Test-Path -LiteralPath $desktop)) {
            throw 'Open Docker Desktop, wait for the engine to start, then run start.bat again.'
        }
        Start-Process -FilePath $desktop -WindowStyle Hidden | Out-Null
        $deadline = (Get-Date).AddSeconds(120)
        while (-not (Test-Docker)) {
            if ((Get-Date) -ge $deadline) { throw 'Docker Desktop did not start within 120 seconds. Open it to check the engine.' }
            Start-Sleep -Seconds 3
        }
    }
    & docker compose up -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) {
        throw 'Infrastructure did not become healthy. Run docker compose ps and docker compose logs --tail 50.'
    }
    New-Item -Path $runtimeDir -ItemType Directory -Force | Out-Null
    Write-Host '[2/3] Starting backend.'
    Start-ServiceProcess 'backend' 10001 $python '-m uvicorn app.main:app --host 127.0.0.1 --port 10001' (Join-Path $projectRoot 'Skyper-python')
    Write-Host '[3/3] Starting frontend.'
    Start-ServiceProcess 'frontend' 5173 $node.Source ('"' + $vite + '" --host 127.0.0.1 --port 5173 --strictPort') (Join-Path $projectRoot 'Skyper-frontend')
    Write-Host ''
    Write-Host '[OK] Skyper is ready: http://127.0.0.1:5173/' -ForegroundColor Green
    Write-Host 'API docs: http://127.0.0.1:10001/docs'
    Write-Host 'Services run in the background. Use stop.bat to stop them.'
    Write-Host 'Logs: .runtime/backend.stderr.log and .runtime/frontend.stdout.log'
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173/' | Out-Null }
} catch {
    Write-Host ("[FAIL] " + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally { Pop-Location }
