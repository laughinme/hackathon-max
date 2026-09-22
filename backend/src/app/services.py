"""Composition root: builds use cases and adapters once at startup.

Handlers receive the `Services` container through `ServicesMiddleware`
(see `bot/middleware.py`) instead of reaching for a global.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import Config
from application.ports.ai import AIService
from application.ports.classifier import Classifier
from application.ports.clock import Clock
from application.ports.tickets import UnitOfWorkFactory
from application.tickets.change_status import ChangeTicketStatus
from application.tickets.create_ticket import CreateTicket
from application.tickets.queries import GetReporterTicket, ListReporterTickets
from application.tickets.triage_complaint import TriageComplaint
from domain.tickets.sla import SlaPolicy
from infrastructure.ai.stub import StubAIService
from infrastructure.ml.http_classifier import HttpClassifier

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Services:
    """Everything handlers need; built once per process."""

    config: Config
    ai: AIService
    triage: TriageComplaint
    create_ticket: CreateTicket
    change_status: ChangeTicketStatus
    list_tickets: ListReporterTickets
    get_ticket: GetReporterTicket
    closeables: list[Any] = field(default_factory=list)

    async def close(self) -> None:
        for resource in self.closeables:
            await resource.close()


def build_ai(config: Config) -> tuple[AIService, Any | None]:
    """Hosted LLM (DECISIONS D-007) or the rule-based stub."""

    if not config.llm_enabled:
        logger.info("AI layer: StubAIService (rules)")
        return StubAIService(), None

    from infrastructure.llm.client import LLMClient, LLMSettings
    from infrastructure.llm.service import LLMAIService

    client = LLMClient(
        LLMSettings(
            base_url=config.llm_base_url,
            model=config.llm_model,
            api_key=config.llm_api_key,
            timeout_sec=config.llm_timeout_sec,
            temperature=config.llm_temperature,
        )
    )
    logger.info("AI layer: hosted LLM %s, fallback StubAIService", config.llm_model)
    return LLMAIService(client, fallback=StubAIService()), client


def build_classifier(config: Config) -> HttpClassifier:
    """ML service over HTTP with rule-based fallback (DECISIONS D-005, D-006)."""

    return HttpClassifier(
        base_url=config.ml_service_url,
        timeout_sec=config.ml_service_timeout_sec,
    )


def build_services(
    config: Config,
    *,
    uow_factory: UnitOfWorkFactory,
    clock: Clock,
    classifier: Classifier | None = None,
    ai: AIService | None = None,
) -> Services:
    closeables: list[Any] = []

    if ai is None:
        ai, llm_client = build_ai(config)
        if llm_client is not None:
            closeables.append(llm_client)

    if classifier is None:
        http_classifier = build_classifier(config)
        closeables.append(http_classifier)
        classifier = http_classifier

    sla = SlaPolicy()
    return Services(
        config=config,
        ai=ai,
        triage=TriageComplaint(classifier, sla, clock, config.ml_confidence_threshold),
        create_ticket=CreateTicket(uow_factory, sla, clock),
        change_status=ChangeTicketStatus(uow_factory, clock),
        list_tickets=ListReporterTickets(uow_factory, clock),
        get_ticket=GetReporterTicket(uow_factory, clock),
        closeables=closeables,
    )
