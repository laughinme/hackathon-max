from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from application.housing.identity import Identity


class ResidencyOut(BaseModel):
    building_id: UUID
    building_code: str
    address: str
    company_name: str
    company_phone: str


class DispatcherOut(BaseModel):
    company_id: UUID
    company_name: str


class MeOut(BaseModel):
    max_user_id: int
    residency: ResidencyOut | None
    dispatcher: DispatcherOut | None
    demo_mode: bool

    @classmethod
    def from_identity(cls, identity: Identity, demo_mode: bool) -> MeOut:
        residency = identity.residency
        dispatcher = identity.dispatcher
        return cls(
            max_user_id=identity.max_user_id,
            residency=ResidencyOut(
                building_id=residency.building_id,
                building_code=residency.building_code,
                address=residency.address,
                company_name=residency.company_name,
                company_phone=residency.company_phone,
            )
            if residency
            else None,
            dispatcher=DispatcherOut(
                company_id=dispatcher.company_id, company_name=dispatcher.company_name
            )
            if dispatcher
            else None,
            demo_mode=demo_mode,
        )
