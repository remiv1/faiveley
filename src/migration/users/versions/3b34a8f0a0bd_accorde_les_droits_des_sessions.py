"""Accorde les droits applicatifs sur les tables d'authentification.

Revision ID: 3b34a8f0a0bd
Revises: f075ed3e6f6f
Create Date: 2026-09-14 17:00:00.000000
""" # pylint: disable=invalid-name

import os
import re
from typing import Sequence

from alembic import op


revision: str = "3b34a8f0a0bd"  # pylint: disable=invalid-name
down_revision: str | None = "f075ed3e6f6f"  # pylint: disable=invalid-name
branch_labels: Sequence[str] | None = None  # pylint: disable=invalid-name
depends_on: Sequence[str] | None = None  # pylint: disable=invalid-name


def _application_role() -> str:
    role = os.environ.get("POSTGRES_USER_APP", "")
    if not re.fullmatch(r"[A-Za-z_]\w*", role, re.ASCII):
        raise RuntimeError("POSTGRES_USER_APP doit être un identifiant PostgreSQL valide.")
    return role


def upgrade() -> None:
    """Accorde les droits de lecture et d'écriture au rôle applicatif."""
    application_role = _application_role()
    op.execute(  # type: ignore[attr-defined] # pylint: disable=no-member
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "
        f"auth_schema TO {application_role}"
    )


def downgrade() -> None:
    """Retire les droits de lecture et d'écriture du rôle applicatif."""
    application_role = _application_role()
    op.execute(  # type: ignore[attr-defined] # pylint: disable=no-member
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "
        f"auth_schema FROM {application_role}"
    )
