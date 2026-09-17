import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("discord_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("handle", sa.String(64), nullable=False, unique=True),
        sa.Column("exp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("money", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_solve_date", sa.Date(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "solved_problems",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True),
        sa.Column("contest_id", sa.Integer(), primary_key=True),
        sa.Column("index", sa.String(8), primary_key=True),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "daily_problems",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("rating", sa.Integer(), primary_key=True),
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("index", sa.String(8), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
    )
    op.create_table(
        "guild_roles",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("rank_name", sa.String(32), primary_key=True),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "cf_cache",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.discord_id"), primary_key=True, autoincrement=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("max_rating", sa.Integer(), nullable=True),
        sa.Column("rank", sa.String(64), nullable=True),
        sa.Column("max_rank", sa.String(64), nullable=True),
        sa.Column("last_online", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "problemset_cache",
        sa.Column("contest_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("index", sa.String(8), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problemset_cache_rating", "problemset_cache", ["rating"])


def downgrade() -> None:
    op.drop_index("ix_problemset_cache_rating", table_name="problemset_cache")
    op.drop_table("problemset_cache")
    op.drop_table("cf_cache")
    op.drop_table("guild_roles")
    op.drop_table("daily_problems")
    op.drop_table("solved_problems")
    op.drop_table("users")
