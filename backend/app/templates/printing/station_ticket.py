"""
printing/templates/station_ticket.py — KDS station ticket template
─────────────────────────────────────────────────────────────────────────────
Large, high-contrast chit printed (or displayed) at the kitchen station.
Optimised for readability at a distance under kitchen lighting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TicketItem:
    name: str
    quantity: int
    variant: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    note: Optional[str] = None


@dataclass
class StationTicketData:
    station_name: str
    station_color: str           # hex, e.g. "#3B82F6"
    order_id: int
    ticket_number: str           # e.g. "GRL-047"
    table_label: str             # "Table 5" / "Counter" / "Takeaway"
    order_type: str
    sent_at: datetime
    items: list[TicketItem]
    priority: int = 0            # 0=normal, 1=rush, 2=vip
    estimated_minutes: int = 10


def render_station_ticket(data: StationTicketData) -> str:
    priority_badge = ""
    if data.priority == 2:
        priority_badge = "<div class='badge vip'>VIP</div>"
    elif data.priority == 1:
        priority_badge = "<div class='badge rush'>RUSH</div>"

    items_html = ""
    for item in data.items:
        variant_line = f"<span class='variant'>({item.variant})</span>" if item.variant else ""
        mods = "".join(f"<li>{m}</li>" for m in item.modifiers)
        mod_block = f"<ul class='mods'>{mods}</ul>" if mods else ""
        note_block = f"<p class='note'>NOTE: {item.note}</p>" if item.note else ""
        items_html += f"""
        <div class='item'>
          <span class='qty'>{item.quantity}×</span>
          <div class='desc'>
            <strong>{item.name}</strong> {variant_line}
            {mod_block}{note_block}
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Ticket {data.ticket_number}</title>
<style>
  @page {{ size: 80mm auto; margin: 4mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; font-size: 14px; width: 72mm; }}
  .header {{ background: {data.station_color}; color: #fff; padding: 6px 8px; border-radius: 4px; }}
  .station {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
  .ticket-no {{ font-size: 22px; font-weight: bold; }}
  .meta {{ font-size: 13px; margin-top: 4px; display: flex; justify-content: space-between; }}
  .table-label {{ font-size: 18px; font-weight: bold; margin: 8px 0 4px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px;
            font-weight: bold; font-size: 11px; letter-spacing: 1px; margin-bottom: 4px; }}
  .rush {{ background: #FF6B00; color: #fff; }}
  .vip {{ background: #7C3AED; color: #fff; }}
  hr {{ border: none; border-top: 2px solid #000; margin: 6px 0; }}
  .item {{ display: flex; align-items: flex-start; margin-bottom: 8px; }}
  .qty {{ font-size: 22px; font-weight: bold; min-width: 32px; }}
  .desc {{ flex: 1; }}
  .desc strong {{ font-size: 16px; }}
  .variant {{ font-size: 12px; color: #555; }}
  .mods {{ font-size: 12px; color: #333; padding-left: 12px; margin-top: 2px; }}
  .note {{ font-size: 12px; color: #c00; font-weight: bold; margin-top: 2px; }}
  .footer {{ font-size: 11px; color: #777; margin-top: 8px; }}
</style>
</head>
<body>
<div class="header">
  <div class="station">{data.station_name}</div>
  <div class="ticket-no">{data.ticket_number}</div>
  <div class="meta">
    <span>ETA: ~{data.estimated_minutes}min</span>
    <span>{data.sent_at.strftime('%H:%M')}</span>
  </div>
</div>
<div class="table-label">{data.table_label}</div>
{priority_badge}
<hr>
{items_html}
<div class="footer">Order #{data.order_id}</div>
</body>
</html>"""