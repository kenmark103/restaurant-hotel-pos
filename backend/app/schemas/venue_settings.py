
# ═══════════════════════════════════════════════════════════════════════════════
# 2. SCHEMAS  →  app/schemas/venue_settings.py  (create new file)
# ═══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel


class VenueSettingsRead(BaseModel):
    restaurant_name: str
    receipt_footer: str
    logo_url: str | None
    currency: str
    timezone: str
    date_format: str
    tax_rate: float
    tax_inclusive: bool
    tax_label: str

    model_config = {"from_attributes": True}


class VenueSettingsUpdate(BaseModel):
    restaurant_name: str | None = None
    receipt_footer: str | None = None
    logo_url: str | None = None
    currency: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    tax_rate: float | None = None
    tax_inclusive: bool | None = None
    tax_label: str | None = None

