"""Тесты REST API gateway с JWT (Фаза 15).

Запускать ВНУТРИ контейнера api-gateway (там сам сервис слушает localhost:8000):
    docker cp tests/test_api.py arb-api-gateway:/app/
    docker exec arb-api-gateway python -m unittest test_api -v

Использует только stdlib (urllib) — без установки зависимостей.
"""
import json
import os
import unittest
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "http://localhost:8000")


def _req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        status, data = _req(
            "POST", "/api/v1/auth/login",
            body={"email": "test@example.com", "password": "test123"},
        )
        assert status == 200, f"login failed: HTTP {status}"
        cls.token = data["access_token"]

    def test_login_returns_jwt(self):
        self.assertTrue(self.token)

    def test_login_bad_password_rejected(self):
        status, _ = _req("POST", "/api/v1/auth/login",
                         body={"email": "test@example.com", "password": "wrong"})
        self.assertIn(status, (400, 401))

    def test_protected_requires_auth(self):
        status, _ = _req("GET", "/api/v1/trades")
        self.assertEqual(status, 401)

    def test_get_trades_with_jwt(self):
        status, data = _req("GET", "/api/v1/trades?page=1&page_size=5", token=self.token)
        self.assertEqual(status, 200)
        self.assertIn("items", data)

    def test_get_prices_with_jwt(self):
        status, data = _req("GET", "/api/v1/prices?limit=5", token=self.token)
        self.assertEqual(status, 200)
        self.assertIn("items", data)

    def test_health_ok(self):
        status, data = _req("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "healthy")

    # ── /api/v1/config (режим paper для фронтенда) ──
    def test_config_requires_auth(self):
        status, _ = _req("GET", "/api/v1/config")
        self.assertEqual(status, 401)

    def test_config_returns_paper_flag(self):
        status, data = _req("GET", "/api/v1/config", token=self.token)
        self.assertEqual(status, 200)
        self.assertIn("paper", data)
        self.assertIsInstance(data["paper"], bool)

    # ── PUT /api/v1/balance (редактирование балансов в paper-режиме) ──
    # Тесты НЕдеструктивны: проверяют только auth и валидацию, которая
    # срабатывает ДО записи в Redis/БД, поэтому балансы не меняются.
    def test_put_balance_requires_auth(self):
        status, _ = _req("PUT", "/api/v1/balance", body={"balances": {"binance": 1.0}})
        self.assertEqual(status, 401)

    def test_put_balance_rejects_unknown_exchange(self):
        # 400 в paper-режиме (unknown ловится до мутации) либо 403, если paper=false.
        status, _ = _req("PUT", "/api/v1/balance",
                         token=self.token, body={"balances": {"nosuchexchange": 1.0}})
        self.assertIn(status, (400, 403))

    def test_put_balance_rejects_negative(self):
        status, _ = _req("PUT", "/api/v1/balance",
                         token=self.token, body={"balances": {"binance": -5.0}})
        self.assertIn(status, (400, 403))

    def test_put_balance_rejects_empty(self):
        status, _ = _req("PUT", "/api/v1/balance", token=self.token, body={"balances": {}})
        # min_length=1 ⇒ 422 от pydantic (или 403, если paper=false).
        self.assertIn(status, (403, 422))

    # ── PUT /api/v1/settings (allowlist + границы значений) ──
    # Недеструктивно: все запросы ниже обязаны отклоняться ДО записи в БД.
    def test_put_settings_requires_auth(self):
        status, _ = _req("PUT", "/api/v1/settings", body={"min_spread_pct": 0.3})
        self.assertEqual(status, 401)

    def test_put_settings_rejects_unknown_key(self):
        # extra="forbid": раньше неизвестный ключ был молчаливым no-op с 200.
        status, _ = _req("PUT", "/api/v1/settings",
                         token=self.token, body={"nonexistent_key": 1})
        self.assertEqual(status, 422)

    def test_put_settings_rejects_out_of_range(self):
        # max_position_pct ограничен 50: выше — Redis-баланс мог уйти в минус.
        status, _ = _req("PUT", "/api/v1/settings",
                         token=self.token, body={"max_position_pct": 10000})
        self.assertEqual(status, 422)

    def test_put_settings_rejects_removed_legacy_key(self):
        # Мёртвые настройки убраны и из формы, и из allowlist.
        status, _ = _req("PUT", "/api/v1/settings",
                         token=self.token, body={"daily_loss_limit_pct": 5})
        self.assertEqual(status, 422)

    def test_put_settings_roundtrip_current_values(self):
        """PUT текущих же значений: проверяет happy-path без изменения состояния."""
        status, data = _req("GET", "/api/v1/settings", token=self.token)
        self.assertEqual(status, 200)
        payload = {k: data[k] for k in
                   ("min_spread_pct", "max_position_pct",
                    "notification_spread_threshold", "notification_trade_min_pnl")
                   if k in data}
        self.assertTrue(payload, "settings table lacks expected keys")
        status, resp = _req("PUT", "/api/v1/settings", token=self.token, body=payload)
        self.assertEqual(status, 200)
        self.assertEqual(resp["status"], "updated")
        self.assertEqual(resp["not_found"], [])

    # ── GET /api/v1/exchanges: комиссии обязаны совпадать с shared/config.py ──
    def test_exchanges_fees_match_config(self):
        from shared.config import EXCHANGES  # доступен внутри контейнера

        status, data = _req("GET", "/api/v1/exchanges", token=self.token)
        self.assertEqual(status, 200)
        items = {i["exchange"]: i for i in data["items"]}
        self.assertTrue(items)
        for name, item in items.items():
            cfg = EXCHANGES[name]
            self.assertEqual(item["taker_fee_pct"], cfg.taker_fee_pct, name)
            self.assertEqual(item["maker_fee_pct"], cfg.maker_fee_pct, name)
            self.assertEqual(item["withdrawal_usdt"], cfg.withdrawal_usdt, name)

    # ── DELETE /api/v1/trades ── только проверка auth (деструктивно при успехе).
    def test_delete_trades_requires_auth(self):
        status, _ = _req("DELETE", "/api/v1/trades")
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
