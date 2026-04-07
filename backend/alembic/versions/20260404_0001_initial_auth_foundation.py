"""initial auth foundation"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260404_0001"
down_revision = None
branch_labels = None
depends_on = None


user_type_enum = postgresql.ENUM("staff", "customer", name="user_type", create_type=True)
auth_provider_enum = postgresql.ENUM("local", "google", name="auth_provider", create_type=True)
role_enum = postgresql.ENUM("admin", "manager", "cashier", "server", "kitchen", name="role", create_type=True)
staff_status_enum = postgresql.ENUM("invited", "active", "disabled", name="staff_status", create_type=True)

user_type_column_enum = postgresql.ENUM("staff", "customer", name="user_type", create_type=False)
auth_provider_column_enum = postgresql.ENUM("local", "google", name="auth_provider", create_type=False)
role_column_enum = postgresql.ENUM("admin", "manager", "cashier", "server", "kitchen", name="role", create_type=False)
staff_status_column_enum = postgresql.ENUM("invited", "active", "disabled", name="staff_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_type_enum.create(bind, checkfirst=True)
    auth_provider_enum.create(bind, checkfirst=True)
    role_enum.create(bind, checkfirst=True)
    staff_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("user_type", user_type_column_enum, nullable=False),
        sa.Column("auth_provider", auth_provider_column_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", role_column_enum, nullable=False),
        sa.Column("status", staff_status_column_enum, nullable=False, server_default="invited"),
        sa.Column("branch_code", sa.String(length=50), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("google_subject", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("loyalty_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_subject"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("customer_profiles")
    op.drop_table("staff_profiles")
    op.drop_table("users")
    bind = op.get_bind()
    staff_status_enum.drop(bind, checkfirst=True)
    role_enum.drop(bind, checkfirst=True)
    auth_provider_enum.drop(bind, checkfirst=True)
    user_type_enum.drop(bind, checkfirst=True)
