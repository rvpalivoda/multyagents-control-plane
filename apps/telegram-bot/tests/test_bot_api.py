from fastapi.testclient import TestClient

from multyagents_telegram_bot.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_preview_contains_expected_keys() -> None:
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert "api_base_url" in body
    assert "token_present" in body


def test_supported_commands_endpoint() -> None:
    response = client.get("/telegram/commands")
    assert response.status_code == 200
    assert response.json()["commands"] == ["abort", "approve", "cancel", "next", "pause", "resume", "run", "status"]


def test_unknown_command_returns_not_handled() -> None:
    response = client.post("/telegram/command", json={"text": "/unknown 1"})
    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is False
    assert body["command"] == "unknown"


def test_command_without_argument_returns_usage() -> None:
    response = client.post("/telegram/command", json={"text": "/status"})
    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["ok"] is False
    assert body["message"] == "usage: /status <id>"


def test_status_command_calls_api(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200

    def fake_request(*, method, url, json, timeout):  # noqa: ANN001
        assert method == "GET"
        assert url.endswith("/workflow-runs/run-7")
        assert json is None
        assert timeout == 5.0
        return _FakeResponse()

    monkeypatch.setattr("multyagents_telegram_bot.main.httpx.request", fake_request)

    response = client.post("/telegram/command", json={"text": "/status run-7"})
    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["ok"] is True
    assert body["api_method"] == "GET"
    assert body["api_path"] == "/workflow-runs/run-7"


def test_run_command_calls_workflow_runs_with_body(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 201

    def fake_request(*, method, url, json, timeout):  # noqa: ANN001
        assert method == "POST"
        assert url.endswith("/workflow-runs")
        assert json == {"workflow_template_id": 9}
        assert timeout == 5.0
        return _FakeResponse()

    monkeypatch.setattr("multyagents_telegram_bot.main.httpx.request", fake_request)

    response = client.post("/telegram/command", json={"text": "/run 9"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_webhook_extracts_text_and_dispatches(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 404

    def fake_request(*, method, url, json, timeout):  # noqa: ANN001
        assert method == "POST"
        assert url.endswith("/workflow-runs/42/pause")
        assert json is None
        assert timeout == 5.0
        return _FakeResponse()

    monkeypatch.setattr("multyagents_telegram_bot.main.httpx.request", fake_request)

    response = client.post(
        "/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 1001},
                "text": "/pause 42",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["ok"] is False
    assert body["api_status"] == 404


def test_approve_command_maps_to_approval_endpoint(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200

    def fake_request(*, method, url, json, timeout):  # noqa: ANN001
        assert method == "POST"
        assert url.endswith("/approvals/77/approve")
        assert json is None
        assert timeout == 5.0
        return _FakeResponse()

    monkeypatch.setattr("multyagents_telegram_bot.main.httpx.request", fake_request)

    response = client.post("/telegram/command", json={"text": "/approve 77"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_next_command_maps_to_dispatch_ready_endpoint(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200

    def fake_request(*, method, url, json, timeout):  # noqa: ANN001
        assert method == "POST"
        assert url.endswith("/workflow-runs/15/dispatch-ready")
        assert json is None
        assert timeout == 5.0
        return _FakeResponse()

    monkeypatch.setattr("multyagents_telegram_bot.main.httpx.request", fake_request)

    response = client.post("/telegram/command", json={"text": "/next 15"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_cancel_command_maps_to_task_cancel_endpoint(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200

    def fake_request(*, method, url, json, timeout):  # noqa: ANN001
        assert method == "POST"
        assert url.endswith("/tasks/123/cancel")
        assert json is None
        assert timeout == 5.0
        return _FakeResponse()

    monkeypatch.setattr("multyagents_telegram_bot.main.httpx.request", fake_request)

    response = client.post("/telegram/command", json={"text": "/cancel 123"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_webhook_without_text_returns_not_handled() -> None:
    response = client.post(
        "/telegram/webhook",
        json={"message": {"chat": {"id": 1001}}},
    )
    assert response.status_code == 200
    assert response.json()["handled"] is False
