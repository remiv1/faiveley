"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
Revision date: 
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}  # pylint: disable=C0103
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}  # pylint: disable=C0103
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}  # pylint: disable=C0103
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}  # pylint: disable=C0103


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
