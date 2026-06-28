"""Fixtures for RBAC route tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tst.rbac.seed import RbacWorld, seed_rbac_world


@pytest.fixture
def rbac_world(db_session: Session) -> RbacWorld:
    return seed_rbac_world(db_session)
