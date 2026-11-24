[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$environmentFile = Join-Path $projectRoot '.runtime\environment.ps1'
if (Test-Path -LiteralPath $environmentFile) { . $environmentFile }
Push-Location $projectRoot
try {
    Write-Host 'Preparing Skyper and checking services. Keep your network proxy running if required for image downloads.'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $projectRoot 'skyper.ps1') -Action Start -NoBrowser
    if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Check the message above. For image download timeouts, start your network proxy and retry.' }
    $vectorVersion = & docker compose exec -T postgres psql -U postgres -d new_rag -tAc "SELECT extversion FROM pg_extension WHERE extname='vector';"
    if ($LASTEXITCODE -ne 0 -or -not ($vectorVersion -match '\d+\.\d+')) { throw 'PostgreSQL/pgvector verification failed.' }
    Write-Host ('pgvector version: ' + ($vectorVersion -join ' ').Trim())
    $health = Invoke-RestMethod 'http://127.0.0.1:9200/_cluster/health' -TimeoutSec 10
    if ($health.status -notin @('green','yellow')) { throw 'Elasticsearch is not healthy.' }
    $tokens = Invoke-RestMethod 'http://127.0.0.1:9200/_analyze' -Method Post -ContentType 'application/json' -Body '{"analyzer":"ik_smart","text":"Skyper setup check"}' -TimeoutSec 10
    if (-not $tokens.tokens) { throw 'IK analyzer verification failed.' }
    $minio = Invoke-WebRequest 'http://127.0.0.1:9000/minio/health/live' -UseBasicParsing -TimeoutSec 10
    if ($minio.StatusCode -ne 200) { throw 'MinIO verification failed.' }
    # The app creates this lazily on the first upload. Prepare it now so the
    # administrator health screen is ready on a fresh installation too.
    $python = Join-Path $projectRoot 'Skyper-python\.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python.exe -ErrorAction Stop).Source }
    Push-Location (Join-Path $projectRoot 'Skyper-python')
    try {
        & $python -c "from app.engine.storage import storage_service; storage_service._ensure_bucket(storage_service.bucket); print('MinIO application bucket ready')"
        if ($LASTEXITCODE -ne 0) { throw 'MinIO application bucket initialization failed.' }
    } finally { Pop-Location }
    & docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read container status.' }
    @{ CheckedAt = (Get-Date).ToString('o'); PostgreSQL = 'ready'; ElasticsearchIK = 'ready'; MinIO = 'ready'; Frontend = 'ready'; Backend = 'ready' } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot '.runtime\installation-verified.json') -Encoding UTF8
    Write-Host '[OK] Skyper installation and service checks completed: http://127.0.0.1:5173/' -ForegroundColor Green
    Start-Process 'http://127.0.0.1:5173/' | Out-Null
} catch {
    Write-Host ('[FAIL] ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally { Pop-Location }
