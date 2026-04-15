from fastapi import APIRouter
from app.api.routes import (
    auth,
    inventory,
    kitchen,
    payments,
    pos,
    printing,
    products,
    reporting,
    settings,
    settings_product,
    staff,
    audit,
)

api_router = APIRouter()

api_router.include_router(auth.router,       prefix="/auth",       tags=["Auth"])
api_router.include_router(audit.router,            prefix="/audit",      tags=["Audit"])
api_router.include_router(staff.router,      prefix="/staff",      tags=["Staff"])
api_router.include_router(settings.router,   prefix="/settings",   tags=["Settings"])
api_router.include_router(products.router,   prefix="/products",   tags=["Products"])
api_router.include_router(settings_product.router, prefix="/settings/product", tags=["Product Settings"])
api_router.include_router(pos.router,        prefix="/pos",        tags=["POS"])
api_router.include_router(kitchen.router,    prefix="/kitchen",    tags=["Kitchen"])
api_router.include_router(inventory.router,  prefix="/inventory",  tags=["Inventory"])
api_router.include_router(payments.router,   prefix="/payments",   tags=["Payments"])
api_router.include_router(printing.router,   prefix="/print",      tags=["Printing"])
api_router.include_router(reporting.router,  prefix="/reports",    tags=["Reporting"])