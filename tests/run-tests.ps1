# Запуск всех тестов Фазы 15 внутри уже поднятых контейнеров.
# Тесты используют stdlib unittest (+ r-зависимости рантайма), поэтому НЕ требуют
# установки pytest и работают офлайн. Нужны запущенные сервисы (docker compose up -d).
#
#   pwsh tests/run-tests.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$cases = @(
  @{ name = 'test_spread_calculator'; container = 'arb-scanner' },
  @{ name = 'test_pnl_calculator';    container = 'arb-executor' },
  @{ name = 'test_api';               container = 'arb-api-gateway' },
  @{ name = 'test_integration';       container = 'arb-api-gateway' }
)

$failed = 0
foreach ($c in $cases) {
  $file = Join-Path $root "tests/$($c.name).py"
  Write-Host "`n=== $($c.name) → $($c.container) ===" -ForegroundColor Cyan
  docker cp $file "$($c.container):/app/$($c.name).py" | Out-Null
  docker exec $c.container python -m unittest $c.name -v
  if ($LASTEXITCODE -ne 0) { $failed++ }
  docker exec $c.container rm -f "/app/$($c.name).py" | Out-Null
}

Write-Host ""
if ($failed -eq 0) { Write-Host "ВСЕ НАБОРЫ ТЕСТОВ ПРОШЛИ" -ForegroundColor Green }
else { Write-Host "$failed набор(ов) тестов УПАЛ(И)" -ForegroundColor Red; exit 1 }
