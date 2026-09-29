param(
    [ValidateSet('Bugs', 'Analytics', 'Commerce', 'All')]
    [string]$Mode = 'Bugs'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    Write-Host 'CommerceHub regression tests use the disposable *_test database.'
    Write-Host 'That test database will be recreated; application data is not seeded or reset.'
    & docker compose --profile test build backend-test
    if ($LASTEXITCODE -ne 0) { throw 'Cannot build backend-test' }
    $testArgs = @('compose', '--profile', 'test', 'run', '--rm', '--entrypoint', 'pytest', 'backend-test', '-q')
    if ($Mode -in @('Bugs', 'Analytics')) {
        $testArgs += @('tests/integration/test_merchant_analytics.py', 'tests/integration/test_analytics_edge_cases.py')
    }
    if ($Mode -in @('Bugs', 'Commerce')) {
        $testArgs += @('tests/integration/test_common_bug_regressions.py', 'tests/integration/test_phase4_commerce.py')
    }
    $testArgs += '-ra'
    & docker @testArgs
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed; see pytest output above.' }
    Write-Host 'Regression tests passed.'
} finally {
    Pop-Location
}
