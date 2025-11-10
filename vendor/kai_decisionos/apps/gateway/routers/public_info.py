from __future__ import annotations

from fastapi import APIRouter

from apps.onboarding.service import (
    get_status_summary,
    get_support_contacts,
    get_pricing_catalog,
)


router = APIRouter(prefix="/api/v1", tags=["public"])


@router.get("/status")
def status_api():
    return get_status_summary()


@router.get("/support")
def support_api():
    return get_support_contacts()


@router.get("/pricing")
def pricing_api():
    return get_pricing_catalog()

