"""menu variants, stock movements, order discounts, pos extensions"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260415_0006"
down_revision = "20260410_0005"
branch_labels = None
depends_on = None


# ── new enums ──────────────────────────────────────────────────────────────────
stock_movement_type_enum = postgresql.ENUM(
    "purchase",
    "sale",
    "return_in",
    "adjustment",
    "waste",
    "transfer",
    name="stock_movement_type",
    create_type=True,
)
discount_type_enum = postgresql.ENUM(
    "percent",
    "fixed",
    name="discount_type",
    create_type=True,
)

# column-only references (create_type=False)
stock_movement_type_col = postgresql.ENUM(
    "purchase", "sale", "return_in", "adjustment", "waste", "transfer",
    name="stock_movement_type", create_type=False,
)
discount_type_col = postgresql.ENUM(
    "percent", "fixed",
    name="discount_type", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    stock_movement_type_enum.create(bind, checkfirst=True)
    discount_type_enum.create(bind, checkfirst=True)

    # ── 1. menu_categories: add parent_id for subcategory hierarchy ────────────
    op.add_column(
        "menu_categories",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_menu_categories_parent_id",
        "menu_categories", "menu_categories",
        ["parent_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── 2. menu_items: extend product record ───────────────────────────────────
    op.add_column("menu_items", sa.Column("barcode", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_menu_items_barcode", "menu_items", ["barcode"])

    op.add_column(
        "menu_items",
        sa.Column("unit_of_measure", sa.String(30), nullable=False, server_default="piece"),
    )
    op.add_column(
        "menu_items",
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "menu_items",
        sa.Column("track_inventory", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "menu_items",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=True),
    )

    # ── 3. menu_item_variants ──────────────────────────────────────────────────
    op.create_table(
        "menu_item_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),          # "Large", "Medium", "Small"
        sa.Column("sell_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("sku", sa.String(50), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_menu_item_variants_menu_item_id", "menu_item_variants", ["menu_item_id"])

    # ── 4. stock_movements ─────────────────────────────────────────────────────
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        # quantity: positive = stock in, negative = stock out
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("movement_type", stock_movement_type_col, nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=True),
        # reference_type: "order" | "purchase_order" | "manual" | "adjustment"
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["menu_item_variants.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_branch_item", "stock_movements", ["branch_id", "menu_item_id"])
    op.create_index("ix_stock_movements_reference", "stock_movements", ["reference_type", "reference_id"])

    # ── 5. order_discounts ─────────────────────────────────────────────────────
    op.create_table(
        "order_discounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        # null order_item_id = order-level discount; set = line-level discount
        sa.Column("order_item_id", sa.Integer(), nullable=True),
        sa.Column("discount_type", discount_type_col, nullable=False),
        # value: 10.00 means 10% (if percent) or KES 10 (if fixed)
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        # computed discount amount stored for audit
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("authorized_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["order_id"], ["pos_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["pos_order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["authorized_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_discounts_order_id", "order_discounts", ["order_id"])

    # ── 6. pos_orders: add room/customer/discount columns ─────────────────────
    op.add_column(
        "pos_orders",
        sa.Column("room_number", sa.String(20), nullable=True),
    )
    op.add_column(
        "pos_orders",
        sa.Column("customer_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "pos_orders",
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )

    # ── 7. pos_order_items: add variant columns ────────────────────────────────
    op.add_column(
        "pos_order_items",
        sa.Column("variant_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pos_order_items",
        sa.Column("variant_name", sa.String(100), nullable=True),
    )
    op.create_foreign_key(
        "fk_pos_order_items_variant_id",
        "pos_order_items", "menu_item_variants",
        ["variant_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_pos_order_items_variant_id", "pos_order_items", type_="foreignkey")
    op.drop_column("pos_order_items", "variant_name")
    op.drop_column("pos_order_items", "variant_id")

    op.drop_column("pos_orders", "discount_total")
    op.drop_column("pos_orders", "customer_name")
    op.drop_column("pos_orders", "room_number")

    op.drop_index("ix_order_discounts_order_id", table_name="order_discounts")
    op.drop_table("order_discounts")

    op.drop_index("ix_stock_movements_reference", table_name="stock_movements")
    op.drop_index("ix_stock_movements_branch_item", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_menu_item_variants_menu_item_id", table_name="menu_item_variants")
    op.drop_table("menu_item_variants")

    op.drop_column("menu_items", "low_stock_threshold")
    op.drop_column("menu_items", "track_inventory")
    op.drop_column("menu_items", "cost_price")
    op.drop_column("menu_items", "unit_of_measure")
    op.drop_unique_constraint("uq_menu_items_barcode", "menu_items")
    op.drop_column("menu_items", "barcode")

    op.drop_constraint("fk_menu_categories_parent_id", "menu_categories", type_="foreignkey")
    op.drop_column("menu_categories", "parent_id")

    bind = op.get_bind()
    discount_type_enum.drop(bind, checkfirst=True)
    stock_movement_type_enum.drop(bind, checkfirst=True)