"""Bodies of the house endpoints: building choice, pulse, leaflet, privacy."""

from __future__ import annotations

from pydantic import BaseModel, Field

from application.tickets.pulse import Pulse
from domain.housing.entities import Building


class BuildingOut(BaseModel):
    code: str
    address: str

    @classmethod
    def from_building(cls, building: Building) -> BuildingOut:
        return cls(code=building.code, address=building.address)


class ResidencyIn(BaseModel):
    building_code: str = Field(
        min_length=1, max_length=64, description="Code from the QR in the entrance"
    )


class CategoryCountOut(BaseModel):
    category_code: str
    count: int


class PulseOut(BaseModel):
    period_days: int
    total: int
    open: int
    overdue: int
    fixed: int
    fixed_on_time: int
    on_time_share: float | None = Field(description="0..1, null when nothing fixed")
    average_fix_hours: float | None
    top_categories: list[CategoryCountOut]
    neighbours_joined: int

    @classmethod
    def from_pulse(cls, pulse: Pulse) -> PulseOut:
        return cls(
            period_days=pulse.period_days,
            total=pulse.total,
            open=pulse.open,
            overdue=pulse.overdue,
            fixed=pulse.fixed,
            fixed_on_time=pulse.fixed_on_time,
            on_time_share=pulse.on_time_share,
            average_fix_hours=pulse.average_fix_hours,
            top_categories=[
                CategoryCountOut(category_code=code, count=count)
                for code, count in pulse.top_categories
            ],
            neighbours_joined=pulse.neighbours_joined,
        )


class HouseOut(BaseModel):
    building_code: str
    address: str
    company_name: str
    company_phone: str
    pulse: PulseOut
    leaflet_path: str = Field(
        description="Signed path of the printable QR leaflet (PDF), no auth header "
        "needed: MAX `downloadFile` cannot send one"
    )
    leaflet_filename: str


class ForgetOut(BaseModel):
    detached_tickets: int = Field(description="Tickets that lost the link to the user")
