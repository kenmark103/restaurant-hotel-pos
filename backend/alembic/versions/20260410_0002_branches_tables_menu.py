"""branches tables menu categories and items"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260410_0002"
down_revision = "20260404_0001"
branch_labels = None
depends_on = None


table_status_enum = postgresql.ENUM(
    "available",
    "occupied",
    "reserved",
    "cleaning",
    name="table_status",
    create_type=True,
)
kitchen_station_enum = postgresql.ENUM(
    "grill",
    "fryer",
    "bar",
    "cold",
    "pass",
    "any",
    name="kitchen_station",
    create_type=True,
)
table_status_col = postgresql.ENUM(
    "available",
    "occupied",
    "reserved",
    "cleaning",
    name="table_status",
    create_type=False,
)
kitchen_station_col = postgresql.ENUM(
    "grill",
    "fryer",
    "bar",
    "cold",
    "pass",
    "any",
    name="kitchen_station",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    table_status_enum.create(bind, checkfirst=True)
    kitchen_station_enum.create(bind, checkfirst=True)

    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Africa/Nairobi"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.add_column("staff_profiles", sa.Column("branch_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_staff_profiles_branch_id_branches", "staff_profiles", "branches", ["branch_id"], ["id"])
    op.drop_column("staff_profiles", "branch_code")

    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("table_number", sa.String(length=20), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", table_status_col, nullable=False, server_default="available"),
        sa.Column("qr_code_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qr_code_token"),
    )

    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("available_from", sa.String(length=5), nullable=True),
        sa.Column("available_until", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("sku", sa.String(length=50), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prep_time_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("station", kitchen_station_col, nullable=False, server_default="any"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["category_id"], ["menu_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )


def downgrade() -> None:
    op.drop_table("menu_items")
    op.drop_table("menu_categories")
    op.drop_table("tables")

    op.add_column("staff_profiles", sa.Column("branch_code", sa.String(length=50), nullable=True))
    op.drop_constraint("fk_staff_profiles_branch_id_branches", "staff_profiles", type_="foreignkey")
    op.drop_column("staff_profiles", "branch_id")

    op.drop_table("branches")

    bind = op.get_bind()
    kitchen_station_enum.drop(bind, checkfirst=True)
    table_status_enum.drop(bind, checkfirst=True)
