"""
API Routes Package
"""
from fastapi import APIRouter

from .disruptions import router as disruptions_router
from .approvals import router as approvals_router
from .flights import router as flights_router
from .awbs import router as awbs_router
from .dev_console import router as dev_console_router
from .recovery import router as recovery_router

api_router = APIRouter()

api_router.include_router(disruptions_router, prefix="/disruptions", tags=["disruptions"])
api_router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
api_router.include_router(flights_router, prefix="/flights", tags=["flights"])
api_router.include_router(awbs_router, prefix="/awbs", tags=["awbs"])
api_router.include_router(dev_console_router, prefix="/dev-console", tags=["dev-console"])
api_router.include_router(recovery_router, tags=["recovery"])
