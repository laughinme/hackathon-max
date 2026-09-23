"""Delete what the service knows about a person, on their request."""

from __future__ import annotations

from application.ports.unit_of_work import UnitOfWorkFactory


class ForgetUser:
    """Removes the building binding and roles; tickets stay with the company as
    records about the building but lose the link to the person (they are
    obligations of the company, and neighbours may have supported them).
    The conversation state is cleared by the bot adapter itself."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, max_user_id: int) -> int:
        async with self._uow_factory() as uow:
            await uow.housing.delete_resident(max_user_id)
            await uow.housing.delete_dispatcher(max_user_id)
            detached = await uow.tickets.detach_reporter(max_user_id)
            await uow.commit()
        return detached
