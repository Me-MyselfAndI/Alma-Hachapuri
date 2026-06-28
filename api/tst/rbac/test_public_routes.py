"""Public routes must not require Bearer token (401)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from tst.rbac.catalog import PUBLIC_ROUTES
from tst.rbac.helpers import invoke, path_for
from tst.rbac.seed import RbacWorld


@pytest.fixture
def bare_client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize(
    "spec",
    PUBLIC_ROUTES,
    ids=lambda s: s.route_id,
)
def test_public_route_does_not_require_auth(
    bare_client: TestClient,
    rbac_world: RbacWorld,
    spec,
) -> None:
    """Intake (L1a/L1b) and login (A1) stay reachable without credentials."""
    if spec.route_id == "L1a":
        with patch("src.domains.lead.service.EmailService.send_verification_email"):
            response = invoke(bare_client, spec, rbac_world)
    else:
        response = invoke(bare_client, spec, rbac_world)

    if response.status_code == 401:
        detail = (
            response.json().get("detail")
            if response.headers.get("content-type", "").startswith("application/json")
            else None
        )
        assert detail != "Could not validate credentials", (
            f"{spec.route_id} {spec.method} {path_for(spec, rbac_world)} "
            f"must not require Bearer token (OAuth2 gate), got 401"
        )
