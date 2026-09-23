"""Composition root: builds use cases and adapters once at startup.

Handlers receive the `Services` container through `ServicesMiddleware`
(bot) or `request.app.state` (HTTP) instead of reaching for a global.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import Config
from application.housing.bind_resident import BindResident
from application.housing.demo import BecomeDemoDispatcher, ListDemoBuildings
from application.housing.identity import IdentifyUser
from application.ports.ai import AIService
from application.ports.classifier import Classifier
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.build_escalation_document import BuildEscalationDocument
from application.tickets.change_status import ChangeTicketStatus
from application.tickets.create_ticket import CreateTicket
from application.tickets.demo_expire_deadline import DemoExpireDeadline
from application.tickets.detect_overdue import DetectOverdueTickets
from application.tickets.escalate_ticket import EscalateTicket
from application.tickets.queries import (
    GetTicketForUser,
    ListDispatcherQueue,
    ListReporterTickets,
)
from application.tickets.triage_complaint import TriageComplaint
from domain.tickets.sla import SlaPolicy
from infrastructure.ai.stub import StubAIService
from infrastructure.llm.classifier import LlmClassifier
from infrastructure.llm.client import LLMClient, LLMSettings
from infrastructure.llm.service import LLMAIService
from infrastructure.ml.http_classifier import HttpClassifier
from infrastructure.ml.rule_based import RuleBasedClassifier
from infrastructure.pdf.escalation import PdfEscalationRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Services:
    """Everything adapters need; built once per process."""

    config: Config
    clock: Clock
    ai: AIService
    triage: TriageComplaint
    create_ticket: CreateTicket
    change_status: ChangeTicketStatus
    list_tickets: ListReporterTickets
    get_ticket: GetTicketForUser
    list_queue: ListDispatcherQueue
    escalate: EscalateTicket
    escalation_document: BuildEscalationDocument
    detect_overdue: DetectOverdueTickets
    demo_expire_deadline: DemoExpireDeadline
    identify: IdentifyUser
    bind_resident: BindResident
    become_demo_dispatcher: BecomeDemoDispatcher
    list_demo_buildings: ListDemoBuildings
    closeables: list[Any] = field(default_factory=list)

    async def close(self) -> None:
        for resource in self.closeables:
            await resource.close()


def build_llm_client(config: Config) -> LLMClient | None:
    """One client for the dialog layer and the classifier; None when unused."""

    if not (config.llm_enabled or config.classifier == "llm"):
        return None
    return LLMClient(
        LLMSettings(
            base_url=config.llm_base_url,
            model=config.llm_model,
            api_key=config.llm_api_key,
            timeout_sec=config.llm_timeout_sec,
            temperature=config.llm_temperature,
        )
    )


def build_ai(config: Config, client: LLMClient | None) -> AIService:
    """Hosted LLM (DECISIONS D-007) or the rule-based stub."""

    if not config.llm_enabled or client is None:
        logger.info("AI layer: StubAIService (rules)")
        return StubAIService()
    logger.info("AI layer: hosted LLM %s, fallback StubAIService", config.llm_model)
    return LLMAIService(client, fallback=StubAIService())


def build_classifier(
    config: Config, client: LLMClient | None
) -> tuple[Classifier, Any | None]:
    """The classifier chosen by `CLASSIFIER` (DECISIONS D-005, D-006, Q-18).

    Every option falls back to keyword rules, so a dead ML service or LLM
    makes classification worse but never stops the bot.
    """

    if config.classifier == "llm" and client is not None:
        logger.info("Classifier: hosted LLM %s, fallback rules", config.llm_model)
        return LlmClassifier(client), None
    if config.classifier == "rules":
        logger.info("Classifier: keyword rules")
        return RuleBasedClassifier(), None
    logger.info("Classifier: CatBoost at %s, fallback rules", config.ml_service_url)
    http = HttpClassifier(
        base_url=config.ml_service_url,
        timeout_sec=config.ml_service_timeout_sec,
    )
    return http, http


def build_services(
    config: Config,
    *,
    uow_factory: UnitOfWorkFactory,
    queries: TicketQueries,
    clock: Clock,
    classifier: Classifier | None = None,
    ai: AIService | None = None,
) -> Services:
    closeables: list[Any] = []

    llm_client = None
    if ai is None or classifier is None:
        llm_client = build_llm_client(config)
        if llm_client is not None:
            closeables.append(llm_client)

    if ai is None:
        ai = build_ai(config, llm_client)

    if classifier is None:
        classifier, resource = build_classifier(config, llm_client)
        if resource is not None:
            closeables.append(resource)

    sla = SlaPolicy()
    return Services(
        config=config,
        clock=clock,
        ai=ai,
        triage=TriageComplaint(classifier, sla, clock, config.ml_confidence_threshold),
        create_ticket=CreateTicket(uow_factory, queries, sla, clock),
        change_status=ChangeTicketStatus(uow_factory, queries, clock),
        list_tickets=ListReporterTickets(queries, clock),
        get_ticket=GetTicketForUser(uow_factory, queries, clock),
        list_queue=ListDispatcherQueue(uow_factory, queries, clock),
        escalate=EscalateTicket(uow_factory, queries, clock),
        escalation_document=BuildEscalationDocument(
            uow_factory, queries, PdfEscalationRenderer(), clock
        ),
        detect_overdue=DetectOverdueTickets(uow_factory, clock),
        demo_expire_deadline=DemoExpireDeadline(
            uow_factory, queries, clock, demo_mode=config.demo_mode
        ),
        identify=IdentifyUser(uow_factory),
        bind_resident=BindResident(uow_factory, clock),
        become_demo_dispatcher=BecomeDemoDispatcher(uow_factory, clock),
        list_demo_buildings=ListDemoBuildings(uow_factory),
        closeables=closeables,
    )
