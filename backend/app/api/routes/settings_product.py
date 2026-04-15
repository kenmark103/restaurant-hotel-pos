"""
routes/settings_product.py — Catalogue configuration endpoints
─────────────────────────────────────────────────────────────────────────────
Prefix: /settings/product
Manages the catalogue prerequisites: units of measure, kitchen stations,
inventory policy, and tax templates.

Changes from uploaded file:
  • Added require_manager auth guards on mutating endpoints.
  • Replaced bare `try/except ValueError` with catches on the correct
    ServiceError subclasses (NotFoundError, ConflictError, ValidationError)
    — the service raises these, not ValueError.
  • JSON deserialisation for alert_recipients and target_ids moved to a
    shared helper (schemas/settings_product.deserialize_json_list).
  • Reorder endpoints renamed to POST (not PATCH) — PATCH on a collection
    endpoint without an ID is ambiguous in OpenAPI.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_manager
from app.db.models import User
from app.db.session import get_db
from app.schemas.settings_product import (
    InventoryPolicyResponse,
    InventoryPolicyUpdate,
    KitchenStationCreate,
    KitchenStationResponse,
    KitchenStationUpdate,
    ProductConfigurationResponse,
    StationReorderPayload,
    TaxTemplateCreate,
    TaxTemplateResponse,
    TaxTemplateUpdate,
    UnitOfMeasureCreate,
    UnitOfMeasureResponse,
    UnitOfMeasureUpdate,
    UnitReorderPayload,
    deserialize_json_list,
)
from app.services.base import ConflictError, NotFoundError, ValidationError
from app.services.settings_product import SettingsProductService

router = APIRouter()


def _svc(db: Annotated[AsyncSession, Depends(get_db)]) -> SettingsProductService:
    return SettingsProductService(db)


# ─────────────────────────────────────────────────────────────────────────────
# Bulk configuration  (no auth — used on public kiosk boot)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/configuration", response_model=ProductConfigurationResponse)
async def get_configuration(svc: Annotated[SettingsProductService, Depends(_svc)]):
    """Return all catalogue config in one DB round-trip (units, stations, policy, taxes)."""
    raw = await svc.get_configuration()

    # Deserialise JSON-string fields before Pydantic validation
    policy = raw["inventory_policy"]
    policy.alert_recipients = deserialize_json_list(policy.alert_recipients)

    for tax in raw["tax_templates"]:
        tax.target_ids = deserialize_json_list(tax.target_ids)

    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Units of measure
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/units", response_model=list[UnitOfMeasureResponse])
async def get_units(
    active_only: bool = False,
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    return await svc.get_units(active_only=active_only)


@router.post("/units", response_model=UnitOfMeasureResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    payload: UnitOfMeasureCreate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        return await svc.create_unit(payload.model_dump())
    except ConflictError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)


@router.patch("/units/{unit_id}", response_model=UnitOfMeasureResponse)
async def update_unit(
    unit_id: str,
    payload: UnitOfMeasureUpdate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        return await svc.update_unit(unit_id, payload.model_dump(exclude_unset=True))
    except NotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: str,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        await svc.delete_unit(unit_id)
    except (NotFoundError, ValidationError) as exc:
        from fastapi import HTTPException
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message)


@router.post("/units/reorder", response_model=list[UnitOfMeasureResponse])
async def reorder_units(
    payload: UnitReorderPayload,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    return await svc.reorder_units(payload.ordered_ids)


# ─────────────────────────────────────────────────────────────────────────────
# Kitchen stations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stations", response_model=list[KitchenStationResponse])
async def get_stations(
    active_only: bool = False,
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    return await svc.get_stations(active_only=active_only)


@router.post("/stations", response_model=KitchenStationResponse, status_code=status.HTTP_201_CREATED)
async def create_station(
    payload: KitchenStationCreate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        return await svc.create_station(payload.model_dump())
    except ConflictError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)


@router.patch("/stations/{station_id}", response_model=KitchenStationResponse)
async def update_station(
    station_id: str,
    payload: KitchenStationUpdate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        return await svc.update_station(station_id, payload.model_dump(exclude_unset=True))
    except NotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.delete("/stations/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(
    station_id: str,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        await svc.delete_station(station_id)
    except (NotFoundError, ValidationError) as exc:
        from fastapi import HTTPException
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message)


@router.post("/stations/reorder", response_model=list[KitchenStationResponse])
async def reorder_stations(
    payload: StationReorderPayload,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    return await svc.reorder_stations(payload.ordered_ids)


# ─────────────────────────────────────────────────────────────────────────────
# Inventory policy  (singleton)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/inventory-policy", response_model=InventoryPolicyResponse)
async def get_inventory_policy(svc: Annotated[SettingsProductService, Depends(_svc)]):
    policy = await svc.get_inventory_policy()
    policy.alert_recipients = deserialize_json_list(policy.alert_recipients)
    return policy


@router.patch("/inventory-policy", response_model=InventoryPolicyResponse)
async def update_inventory_policy(
    payload: InventoryPolicyUpdate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    policy = await svc.update_inventory_policy(payload.model_dump(exclude_unset=True))
    policy.alert_recipients = deserialize_json_list(policy.alert_recipients)
    return policy


# ─────────────────────────────────────────────────────────────────────────────
# Tax templates
# ─────────────────────────────────────────────────────────────────────────────

def _deser_tax(tax):
    """Deserialise target_ids JSON string in-place."""
    tax.target_ids = deserialize_json_list(tax.target_ids)
    return tax


@router.get("/taxes", response_model=list[TaxTemplateResponse])
async def get_tax_templates(
    active_only: bool = False,
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    return [_deser_tax(t) for t in await svc.get_tax_templates(active_only=active_only)]


@router.post("/taxes", response_model=TaxTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_template(
    payload: TaxTemplateCreate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    return _deser_tax(await svc.create_tax_template(payload.model_dump()))


@router.patch("/taxes/{tax_id}", response_model=TaxTemplateResponse)
async def update_tax_template(
    tax_id: str,
    payload: TaxTemplateUpdate,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        return _deser_tax(
            await svc.update_tax_template(tax_id, payload.model_dump(exclude_unset=True))
        )
    except NotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.delete("/taxes/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_template(
    tax_id: str,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        await svc.delete_tax_template(tax_id)
    except NotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.post("/taxes/{tax_id}/set-default", response_model=list[TaxTemplateResponse])
async def set_default_tax(
    tax_id: str,
    _: User = Depends(require_manager),
    svc: Annotated[SettingsProductService, Depends(_svc)] = ...,
):
    try:
        return [_deser_tax(t) for t in await svc.set_default_tax(tax_id)]
    except NotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)