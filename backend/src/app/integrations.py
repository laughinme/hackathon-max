"""Composition of the integration layer: the use cases behind /integration/v1,
the dispatcher's connection screen and the webhook relay."""

from __future__ import annotations

from dataclasses import dataclass

from application.integrations.apply_external_status import ApplyExternalStatus
from application.integrations.authenticate import AuthenticateIntegration
from application.integrations.calculate_sla import CalculateSla
from application.integrations.configure_webhook import ConfigureWebhook
from application.integrations.connect_integration import ConnectIntegration
from application.integrations.deliver_webhooks import DeliverWebhooks
from application.integrations.link_ticket import LinkExternalTicket
from application.integrations.ping_webhook import PingWebhook
from application.integrations.queries import (
    DescribeIntegration,
    GetIntegrationTicket,
    ListChangedTickets,
    ListCompanyIntegrations,
    ListIntegrationEvents,
)
from application.integrations.revoke_integration import RevokeIntegration
from application.integrations.set_status_map import SetStatusMap
from application.ports.clock import Clock
from application.ports.integrations import IntegrationFeed, WebhookSender
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.tickets.sla import SlaPolicy


@dataclass(frozen=True)
class IntegrationServices:
    # The dispatcher in the mini-app.
    connect: ConnectIntegration
    revoke: RevokeIntegration
    list_for_dispatcher: ListCompanyIntegrations
    # The connected system, by API key.
    authenticate: AuthenticateIntegration
    describe: DescribeIntegration
    configure_webhook: ConfigureWebhook
    set_status_map: SetStatusMap
    ping_webhook: PingWebhook
    get_ticket: GetIntegrationTicket
    list_tickets: ListChangedTickets
    list_events: ListIntegrationEvents
    link_ticket: LinkExternalTicket
    apply_status: ApplyExternalStatus
    calculate_sla: CalculateSla
    # Background relay.
    deliver_webhooks: DeliverWebhooks


def build_integration_services(
    *,
    uow_factory: UnitOfWorkFactory,
    queries: TicketQueries,
    feed: IntegrationFeed,
    sender: WebhookSender,
    sla: SlaPolicy,
    clock: Clock,
) -> IntegrationServices:
    return IntegrationServices(
        connect=ConnectIntegration(uow_factory, clock),
        revoke=RevokeIntegration(uow_factory),
        list_for_dispatcher=ListCompanyIntegrations(uow_factory, feed),
        authenticate=AuthenticateIntegration(uow_factory),
        describe=DescribeIntegration(feed),
        configure_webhook=ConfigureWebhook(uow_factory, sender),
        set_status_map=SetStatusMap(uow_factory, feed),
        ping_webhook=PingWebhook(sender, clock),
        get_ticket=GetIntegrationTicket(uow_factory, queries, clock),
        list_tickets=ListChangedTickets(queries, feed, clock),
        list_events=ListIntegrationEvents(feed),
        link_ticket=LinkExternalTicket(uow_factory, queries, clock),
        apply_status=ApplyExternalStatus(uow_factory, queries, clock),
        calculate_sla=CalculateSla(sla, clock),
        deliver_webhooks=DeliverWebhooks(feed, sender, uow_factory, clock),
    )
