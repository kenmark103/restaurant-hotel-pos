"""add pos order runtime tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260410_0004"
down_revision = "20260410_0003"
branch_labels = None
depends_on = None


pos_order_status_enum = postgresql.ENUM(
    "open",
    "sent",
    "closed",
    "voided",
    name="pos_order_status",
    create_type=True,
)
payment_method_enum = postgresql.ENUM(
    "cash",
    "mobile_money",
    "card",
    "room_charge",
    name="payment_method",
    create_type=True,
)
pos_order_status_col = postgresql.ENUM(
    "open",
    "sent",
    "closed",
    "voided",
    name="pos_order_status",
    create_type=False,
)
payment_method_col = postgresql.ENUM(
    "cash",
    "mobile_money",
    "card",
    "room_charge",
    name="payment_method",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    pos_order_status_enum.create(bind, checkfirst=True)
    payment_method_enum.create(bind, checkfirst=True)

    op.create_table(
        "pos_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=True),
        sa.Column("staff_user_id", sa.Integer(), nullable=False),
        sa.Column("status", pos_order_status_col, nullable=False, server_default="open"),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", payment_method_col, nullable=True),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pos_orders_branch_status", "pos_orders", ["branch_id", "status"], unique=False)
    op.create_index("ix_pos_orders_table_status", "pos_orders", ["table_id", "status"], unique=False)

    op.create_table(
        "pos_order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("is_voided", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("void_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["pos_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pos_order_items_order_id", "pos_order_items", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pos_order_items_order_id", table_name="pos_order_items")
    op.drop_table("pos_order_items")

    op.drop_index("ix_pos_orders_table_status", table_name="pos_orders")
    op.drop_index("ix_pos_orders_branch_status", table_name="pos_orders")
    op.drop_table("pos_orders")

    bind = op.get_bind()
    payment_method_enum.drop(bind, checkfirst=True)
    pos_order_status_enum.drop(bind, checkfirst=True)
