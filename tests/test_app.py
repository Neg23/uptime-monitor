import requests
from prometheus_client import REGISTRY

import app


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def metric(name, url):
    return REGISTRY.get_sample_value(name, {"url": url})


def test_site_up(monkeypatch):
    url = "https://up.test"
    monkeypatch.setattr(app.requests, "get", lambda u, timeout: FakeResponse(200))

    app.check_site(url)

    assert metric("uptime_site_up", url) == 1
    assert metric("uptime_site_status_code", url) == 200


def test_site_server_error(monkeypatch):
    url = "https://error.test"
    monkeypatch.setattr(app.requests, "get", lambda u, timeout: FakeResponse(500))

    app.check_site(url)

    assert metric("uptime_site_up", url) == 0
    assert metric("uptime_site_status_code", url) == 500


def test_site_unreachable(monkeypatch):
    url = "https://down.test"

    def fake_get(u, timeout):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(app.requests, "get", fake_get)

    app.check_site(url)

    assert metric("uptime_site_up", url) == 0
    assert metric("uptime_site_status_code", url) == 0
