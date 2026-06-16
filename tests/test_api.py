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


if __name__ == "__main__":
    unittest.main()
