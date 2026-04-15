"""
printing/templates/z_report.py — Z-Report daily reconciliation template
─────────────────────────────────────────────────────────────────────────────
A4 landscape PDF suited for manager filing and end-of-day reconciliation.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ZReportData:
    branch_name: str
    branch_code: str
    report_date: date
    generated_at: datetime
    generated_by: str

    # Totals
    total_orders: int
    total_revenue: Decimal
    total_discounts: Decimal
    total_tax: Decimal
    void_count: int
    void_amount: Decimal
    net_revenue: Decimal

    # Payment breakdown
    cash_total: Decimal
    card_total: Decimal
    mobile_money_total: Decimal
    complimentary_total: Decimal

    # Session
    opening_float: Decimal
    closing_float: Decimal
    expected_closing: Decimal
    discrepancy: Decimal

    # Hourly
    hourly: list[dict] = field(default_factory=list)     # [{hour, orders, revenue}]
    top_items: list[dict] = field(default_factory=list)  # [{name, qty, revenue}]

    currency_symbol: str = "KSh"


def render_z_report(data: ZReportData) -> str:
    def m(v: Decimal) -> str:
        return f"{data.currency_symbol} {v:,.2f}"

    disc_class = "red" if data.discrepancy < 0 else "green" if data.discrepancy > 0 else ""
    disc_sign = "+" if data.discrepancy > 0 else ""

    hourly_rows = "".join(
        f"<tr><td>{h['hour']:02d}:00</td><td>{h['orders']}</td><td class='right'>{m(Decimal(str(h['revenue'])))}</td></tr>"
        for h in data.hourly
    )
    top_item_rows = "".join(
        f"<tr><td>{i['name']}</td><td class='right'>{i['qty']}</td><td class='right'>{m(Decimal(str(i['revenue'])))}</td></tr>"
        for i in data.top_items[:10]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Z-Report {data.branch_code} {data.report_date}</title>
<style>
  @page {{ size: A4; margin: 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, sans-serif; font-size: 11px; color: #000; }}
  h1 {{ font-size: 18px; margin-bottom: 2px; }}
  h2 {{ font-size: 13px; margin: 12px 0 4px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 2px; }}
  .meta {{ color: #555; font-size: 10px; margin-bottom: 12px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
  .card {{ border: 1px solid #ddd; border-radius: 4px; padding: 8px; }}
  .card .label {{ font-size: 10px; color: #777; text-transform: uppercase; }}
  .card .value {{ font-size: 16px; font-weight: bold; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
  th {{ background: #f0f0f0; text-align: left; padding: 4px 6px; font-size: 10px; text-transform: uppercase; }}
  td {{ padding: 3px 6px; border-bottom: 1px solid #f0f0f0; }}
  .right {{ text-align: right; }}
  .red {{ color: #c00; }}
  .green {{ color: #060; }}
  .total-row td {{ font-weight: bold; border-top: 2px solid #000; }}
  .signature {{ margin-top: 24px; border-top: 1px solid #000; padding-top: 4px; font-size: 10px; color: #777; }}
</style>
</head>
<body>
<h1>Z-Report — {data.branch_name}</h1>
<div class="meta">
  Date: {data.report_date.strftime('%d %B %Y')} &nbsp;|&nbsp;
  Branch: {data.branch_code} &nbsp;|&nbsp;
  Generated: {data.generated_at.strftime('%d/%m/%Y %H:%M')} &nbsp;|&nbsp;
  By: {data.generated_by}
</div>

<div class="grid">
  <div class="card"><div class="label">Total Revenue</div><div class="value">{m(data.total_revenue)}</div></div>
  <div class="card"><div class="label">Orders</div><div class="value">{data.total_orders}</div></div>
  <div class="card"><div class="label">Voids</div><div class="value" style="color:#c00">{data.void_count} ({m(data.void_amount)})</div></div>
  <div class="card"><div class="label">Discounts</div><div class="value">{m(data.total_discounts)}</div></div>
  <div class="card"><div class="label">{data.tax_label if hasattr(data,'tax_label') else 'VAT'}</div><div class="value">{m(data.total_tax)}</div></div>
  <div class="card"><div class="label">Net Revenue</div><div class="value">{m(data.net_revenue)}</div></div>
</div>

<h2>Payment breakdown</h2>
<table>
  <tr><th>Method</th><th class="right">Amount</th></tr>
  <tr><td>Cash</td><td class="right">{m(data.cash_total)}</td></tr>
  <tr><td>Mobile Money (M-Pesa / Airtel)</td><td class="right">{m(data.mobile_money_total)}</td></tr>
  <tr><td>Card</td><td class="right">{m(data.card_total)}</td></tr>
  <tr><td>Complimentary / Room Charge</td><td class="right">{m(data.complimentary_total)}</td></tr>
  <tr class="total-row"><td>Total</td><td class="right">{m(data.total_revenue)}</td></tr>
</table>

<h2>Cash session reconciliation</h2>
<table>
  <tr><td>Opening float</td><td class="right">{m(data.opening_float)}</td></tr>
  <tr><td>Cash sales</td><td class="right">{m(data.cash_total)}</td></tr>
  <tr><td>Expected closing</td><td class="right">{m(data.expected_closing)}</td></tr>
  <tr><td>Actual closing float</td><td class="right">{m(data.closing_float)}</td></tr>
  <tr class="total-row"><td>Discrepancy</td><td class="right {disc_class}">{disc_sign}{m(data.discrepancy)}</td></tr>
</table>

<h2>Hourly breakdown</h2>
<table>
  <tr><th>Hour</th><th>Orders</th><th class="right">Revenue</th></tr>
  {hourly_rows}
</table>

<h2>Top 10 items</h2>
<table>
  <tr><th>Item</th><th class="right">Qty</th><th class="right">Revenue</th></tr>
  {top_item_rows}
</table>

<div class="signature">Manager signature: ____________________________</div>
</body>
</html>"""