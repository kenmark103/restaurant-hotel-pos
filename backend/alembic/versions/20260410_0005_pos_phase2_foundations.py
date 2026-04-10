"""phase2 foundation: order type payments tax modifiers cash session"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260410_0005"
down_revision = "20260410_0004"
branch_labels = None
depends_on = None


order_type_enum = postgresql.ENUM(
    "dine_in",
    "counter",
    "takeaway",
    "room_charge",
    name="order_type",
    create_type=True,
)
cash_session_status_enum = postgresql.ENUM(
    "open",
    "closed",
    name="cash_session_status",
    create_type=True,
)
payment_method_col = postgresql.ENUM(
    "cash",
    "mobile_money",
    "card",
    "room_charge",
    name="payment_method",
    create_type=False,
)
order_type_col = postgresql.ENUM(
    "dine_in",
    "counter",
    "takeaway",
    "room_charge",
    name="order_type",
    create_type=False,
)
cash_session_status_col = postgresql.ENUM(
    "open",
    "closed",
    name="cash_session_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    order_type_enum.create(bind, checkfirst=True)
    cash_session_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "pos_orders",
        sa.Column("order_type", order_type_col, nullable=False, server_default="dine_in"),
    )

    op.create_table(
        "tax_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=80), nullable=False, server_default="VAT"),
        sa.Column("rate", sa.Numeric(6, 4), nullable=False, server_default="0.1600"),
        sa.Column("is_inclusive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_configs_branch_id", "tax_configs", ["branch_id"], unique=False)
    op.execute(
        sa.text(
            "INSERT INTO tax_configs (branch_id, label, rate, is_inclusive) "
            "VALUES (NULL, 'VAT', 0.1600, false)"
        )
    )

    op.create_table(
        "pos_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("method", payment_method_col, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["order_id"], ["pos_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pos_payments_order_id", "pos_payments", ["order_id"], unique=False)

    op.create_table(
        "menu_modifier_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_selections", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_modifier_groups_menu_item_id", "menu_modifier_groups", ["menu_item_id"], unique=False)

    op.create_table(
        "menu_modifier_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_delta", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["group_id"], ["menu_modifier_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_modifier_options_group_id", "menu_modifier_options", ["group_id"], unique=False)

    op.create_table(
        "pos_order_item_modifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=True),
        sa.Column("option_name", sa.String(length=120), nullable=False),
        sa.Column("price_delta", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["order_item_id"], ["pos_order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_id"], ["menu_modifier_options.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pos_order_item_modifiers_order_item_id",
        "pos_order_item_modifiers",
        ["order_item_id"],
        unique=False,
    )

    op.create_table(
        "cash_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("staff_user_id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_float", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("closing_float", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", cash_session_status_col, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_sessions_branch_id", "cash_sessions", ["branch_id"], unique=False)
    op.create_index("ix_cash_sessions_status", "cash_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cash_sessions_status", table_name="cash_sessions")
    op.drop_index("ix_cash_sessions_branch_id", table_name="cash_sessions")
    op.drop_table("cash_sessions")

    op.drop_index("ix_pos_order_item_modifiers_order_item_id", table_name="pos_order_item_modifiers")
    op.drop_table("pos_order_item_modifiers")

    op.drop_index("ix_menu_modifier_options_group_id", table_name="menu_modifier_options")
    op.drop_table("menu_modifier_options")

    op.drop_index("ix_menu_modifier_groups_menu_item_id", table_name="menu_modifier_groups")
    op.drop_table("menu_modifier_groups")

    op.drop_index("ix_pos_payments_order_id", table_name="pos_payments")
    op.drop_table("pos_payments")

    op.drop_index("ix_tax_configs_branch_id", table_name="tax_configs")
    op.drop_table("tax_configs")

    op.drop_column("pos_orders", "order_type")

    bind = op.get_bind()
    cash_session_status_enum.drop(bind, checkfirst=True)
    order_type_enum.drop(bind, checkfirst=True)
