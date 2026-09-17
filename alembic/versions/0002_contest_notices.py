import sqlalchemy as sa
from alembic import op

revision = "0002_contest_notices"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contest_notices",
        sa.Column("platform", sa.String(32), primary_key=True),
        sa.Column("contest_key", sa.String(64), primary_key=True),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("contest_notices")
