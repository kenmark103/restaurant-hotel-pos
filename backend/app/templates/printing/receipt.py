"""
printing/templates/receipt.py — Customer receipt template
─────────────────────────────────────────────────────────────────────────────
Renders a customer-facing receipt as an HTML string.
PrintingService converts this HTML → PDF via weasyprint (or puppeteer).

Design goals:
  • 80mm thermal-printer compatible when rendered at 302px width
  • Clean, professional layout matching the venue's branding
  • All data comes from a typed ReceiptData dataclass (no raw dict)

Usage:
    data = ReceiptData.from_order(order, venue_settings)
    html = render_receipt(data)
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ReceiptItem:
    name: str
    variant: Optional[str]
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    modifiers: list[str] = field(default_factory=list)
    note: Optional[str] = None


@dataclass
class ReceiptPayment:
    method: str
    amount: Decimal
    reference: Optional[str] = None


@dataclass
class ReceiptData:
    # Venue
    restaurant_name: str
    legal_name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    tax_id: Optional[str]
    logo_url: Optional[str]
    receipt_footer: str
    currency_symbol: str
    show_vat_breakdown: bool
    show_staff_name: bool
    tax_label: str

    # Order
    order_id: int
    receipt_number: str           # e.g. "NRB-00123"
    table_label: Optional[str]    # "Table 5" or "Counter" or "Takeaway"
    order_type: str
    staff_name: Optional[str]
    closed_at: datetime

    # Financials
    items: list[ReceiptItem]
    payments: list[ReceiptPayment]
    subtotal: Decimal
    discount_total: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    change_due: Decimal

    @classmethod
    def from_order(cls, order, venue) -> "ReceiptData":
        """
        Construct from ORM objects.  Call this in the printing service after
        loading the order with all relationships.
        """
        table_label = None
        if order.order_type == "dine_in" and order.table:
            table_label = f"Table {order.table.table_number}"
        elif order.order_type == "takeaway":
            table_label = "Takeaway"
        elif order.order_type == "counter":
            table_label = "Counter"
        elif order.order_type == "room_charge":
            table_label = f"Room {order.room_number}" if order.room_number else "Room Charge"

        items = [
            ReceiptItem(
                name=i.menu_item_name,
                variant=i.variant_name,
                quantity=i.quantity,
                unit_price=i.unit_price,
                line_total=i.line_total,
                modifiers=[m.option_name for m in i.modifiers],
                note=i.note,
            )
            for i in order.items
            if not i.is_voided
        ]

        payments = [
            ReceiptPayment(
                method=p.method.value.replace("_", " ").title(),
                amount=p.amount,
                reference=p.reference,
            )
            for p in order.payments
        ]

        return cls(
            restaurant_name=venue.restaurant_name if venue else "Restaurant",
            legal_name=venue.legal_name if venue else None,
            address=venue.address if venue else None,
            phone=venue.phone if venue else None,
            tax_id=venue.tax_id if venue else None,
            logo_url=venue.receipt_logo_url if venue else None,
            receipt_footer=venue.receipt_footer if venue else "Thank you!",
            currency_symbol=venue.currency_symbol if venue else "KSh",
            show_vat_breakdown=venue.receipt_show_vat_breakdown if venue else True,
            show_staff_name=venue.receipt_show_staff_name if venue else True,
            tax_label=venue.tax_label if venue else "VAT",
            order_id=order.id,
            receipt_number=f"{order.branch_id:02d}-{order.id:05d}",
            table_label=table_label,
            order_type=order.order_type.value,
            staff_name=order.staff_user.full_name if order.staff_user else None,
            closed_at=order.closed_at or datetime.utcnow(),
            items=items,
            payments=payments,
            subtotal=order.subtotal,
            discount_total=order.discount_total,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            amount_paid=order.amount_paid or Decimal("0"),
            change_due=order.change_due or Decimal("0"),
        )


def render_receipt(data: ReceiptData) -> str:
    """Return a complete HTML string for the customer receipt."""

    def money(v: Decimal) -> str:
        return f"{data.currency_symbol} {v:,.2f}"

    items_html = ""
    for item in data.items:
        mod_line = f"<div class='mod'>{', '.join(item.modifiers)}</div>" if item.modifiers else ""
        note_line = f"<div class='note'>{item.note}</div>" if item.note else ""
        variant = f" ({item.variant})" if item.variant else ""
        items_html += f"""
        <tr>
          <td class='desc'>{item.name}{variant}{mod_line}{note_line}</td>
          <td class='qty'>{item.quantity}</td>
          <td class='price'>{money(item.unit_price)}</td>
          <td class='total'>{money(item.line_total)}</td>
        </tr>"""

    payments_html = "".join(
        f"<div class='pay-row'>"
        f"<span>{p.method}</span>"
        f"<span>{money(p.amount)}{' · ' + p.reference if p.reference else ''}</span>"
        f"</div>"
        for p in data.payments
    )

    discount_row = (
        f"<tr class='discount'><td colspan='3'>Discount</td><td>- {money(data.discount_total)}</td></tr>"
        if data.discount_total > 0
        else ""
    )
    tax_row = (
        f"<tr class='tax'><td colspan='3'>{data.tax_label}</td><td>{money(data.tax_amount)}</td></tr>"
        if data.show_vat_breakdown
        else ""
    )
    staff_line = (
        f"<p>Served by: {data.staff_name}</p>" if data.show_staff_name and data.staff_name else ""
    )
    logo_tag = (
        f"<img src='{data.logo_url}' alt='logo' class='logo'>" if data.logo_url else ""
    )
    tax_id_line = f"<p>Tax ID: {data.tax_id}</p>" if data.tax_id else ""
    change_row = (
        f"<tr class='change'><td colspan='3'>Change</td><td>{money(data.change_due)}</td></tr>"
        if data.change_due > 0
        else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Receipt {data.receipt_number}</title>
<style>
  @page {{ size: 80mm auto; margin: 4mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Courier New', monospace; font-size: 11px; color: #000; width: 72mm; }}
  .header {{ text-align: center; margin-bottom: 8px; }}
  .logo {{ max-width: 48mm; margin-bottom: 4px; }}
  .restaurant {{ font-size: 14px; font-weight: bold; }}
  .sub {{ font-size: 10px; color: #444; }}
  hr {{ border: none; border-top: 1px dashed #aaa; margin: 6px 0; }}
  .meta {{ font-size: 10px; margin-bottom: 6px; }}
  .meta span {{ float: right; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font-size: 10px; text-transform: uppercase; border-bottom: 1px solid #000; padding: 2px 0; }}
  td {{ padding: 2px 0; vertical-align: top; }}
  .desc {{ width: 44%; }}
  .qty {{ width: 8%; text-align: center; }}
  .price {{ width: 22%; text-align: right; }}
  .total {{ width: 26%; text-align: right; }}
  .mod {{ font-size: 10px; color: #555; padding-left: 4px; }}
  .note {{ font-size: 10px; color: #555; font-style: italic; padding-left: 4px; }}
  .totals {{ margin-top: 4px; }}
  .totals tr td:first-child {{ font-size: 10px; color: #555; }}
  .totals tr.grand td {{ font-weight: bold; font-size: 13px; border-top: 1px solid #000; }}
  .totals tr.discount td {{ color: #c00; }}
  .totals tr.change td {{ color: #060; }}
  .payments {{ margin-top: 6px; font-size: 10px; }}
  .pay-row {{ display: flex; justify-content: space-between; padding: 1px 0; }}
  .footer {{ margin-top: 8px; text-align: center; font-size: 10px; color: #555; }}
</style>
</head>
<body>
<div class="header">
  {logo_tag}
  <div class="restaurant">{data.restaurant_name}</div>
  {f'<div class="sub">{data.legal_name}</div>' if data.legal_name else ''}
  {f'<div class="sub">{data.address}</div>' if data.address else ''}
  {f'<div class="sub">Tel: {data.phone}</div>' if data.phone else ''}
  {tax_id_line}
</div>
<hr>
<div class="meta">
  Receipt: <strong>{data.receipt_number}</strong><span>{data.closed_at.strftime('%d/%m/%Y %H:%M')}</span>
</div>
{f'<div class="meta">{data.table_label}</div>' if data.table_label else ''}
{staff_line}
<hr>
<table>
  <thead>
    <tr>
      <th class="desc">Item</th><th class="qty">Qty</th>
      <th class="price">Unit</th><th class="total">Total</th>
    </tr>
  </thead>
  <tbody>
    {items_html}
  </tbody>
</table>
<hr>
<table class="totals">
  <tr><td colspan="3">Subtotal</td><td class="total">{money(data.subtotal)}</td></tr>
  {discount_row}
  {tax_row}
  <tr class="grand"><td colspan="3">TOTAL</td><td class="total">{money(data.total_amount)}</td></tr>
  <tr><td colspan="3">Amount Paid</td><td class="total">{money(data.amount_paid)}</td></tr>
  {change_row}
</table>
<hr>
<div class="payments">
  <strong>Payment</strong>
  {payments_html}
</div>
<div class="footer">
  <p>{data.receipt_footer}</p>
</div>
</body>
</html>"""