#!/usr/bin/env bash
# Запуск всех тестов внутри уже поднятых контейнеров (docker compose up -d).
# Тесты используют stdlib unittest (+ зависимости рантайма контейнеров), поэтому
# НЕ требуют установки pytest и работают офлайн.
#
#   bash tests/run-tests.sh
set -u
cd "$(dirname "$0")/.."

CASES=(
  "test_spread_calculator arb-scanner"
  "test_depth arb-scanner"
  "test_pnl_calculator arb-executor"
  "test_paper_trading arb-executor"
  "test_api arb-api-gateway"
  "test_integration arb-api-gateway"
)

failed=0
for entry in "${CASES[@]}"; do
  read -r name container <<<"$entry"
  echo ""
  echo "=== ${name} → ${container} ==="
  docker cp "tests/${name}.py" "${container}:/app/${name}.py" >/dev/null
  if ! docker exec "${container}" python -m unittest "${name}" -v; then
    failed=$((failed + 1))
  fi
  docker exec "${container}" rm -f "/app/${name}.py" >/dev/null
done

echo ""
if [ "${failed}" -eq 0 ]; then
  echo "ВСЕ НАБОРЫ ТЕСТОВ ПРОШЛИ"
else
  echo "${failed} набор(ов) тестов УПАЛ(И)"
  exit 1
fi
