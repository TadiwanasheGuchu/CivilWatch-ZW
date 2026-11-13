from typing import Literal

from pydantic import BaseModel

ComponentStatus = Literal["ok", "unavailable"]


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: ComponentStatus
    postgis: ComponentStatus
    cache: ComponentStatus
