import sqlalchemy as sa
from alembic import op

revision = "0003_user_settings"
down_revision = "0002_contest_notices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True, autoincrement=False),
        sa.Column("solve_announcements", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mention_on_solve", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("nickname_sync", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
