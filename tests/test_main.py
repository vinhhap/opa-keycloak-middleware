from http import HTTPStatus

from fastapi.testclient import TestClient
from fastapi_poetry_starter.main import app
from structlog.testing import capture_logs

client = TestClient(app)


def test_healthcheck():
    response = client.get("/healthcheck")
    assert response.status_code == HTTPStatus.OK
    assert response.text == ""
