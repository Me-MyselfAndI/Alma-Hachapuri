"""401 when no Bearer token on protected routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app
from tst.rbac.catalog import PROTECTED_FOR_UNAUTH
from tst.rbac.helpers import invoke, path_for
from tst.rbac.seed import RbacWorld


@pytest.fixture
def bare_client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize(
    "spec",
    PROTECTED_FOR_UNAUTH,
    ids=lambda s: s.route_id,
)
def test_protected_route_requires_auth(
    bare_client: TestClient,
    rbac_world: RbacWorld,
    spec,
) -> None:
    response = invoke(bare_client, spec, rbac_world)
    assert response.status_code == 401, (
        f"{spec.route_id} {spec.method} {path_for(spec, rbac_world)} "
        f"expected 401 without token, got {response.status_code}"
    )
