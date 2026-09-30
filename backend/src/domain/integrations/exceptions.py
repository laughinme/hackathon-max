"""Integration-specific business-rule violations."""

from __future__ import annotations

from domain.errors import DomainError


class InvalidApiKeyError(DomainError):
    code = "invalid_api_key"

    def __init__(self) -> None:
        super().__init__(
            "Missing, unknown or revoked API key: send 'Authorization: Bearer <key>'"
        )


class IntegrationNotFoundError(DomainError):
    code = "integration_not_found"

    def __init__(self) -> None:
        super().__init__("Integration not found")


class UnknownExternalStatusError(DomainError):
    code = "unknown_status"

    def __init__(self, raw: str) -> None:
        super().__init__(
            f"Unknown status {raw!r}: send one of ours (registered, acknowledged, "
            "in_progress, done, rejected) or add it to the status map"
        )
        self.raw = raw


class ExternalIdTakenError(DomainError):
    code = "external_id_taken"

    def __init__(self, external_id: str) -> None:
        super().__init__(
            f"External id {external_id!r} is already linked to another ticket"
        )


class WebhookUrlRejectedError(DomainError):
    code = "webhook_url_rejected"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Webhook URL rejected: {reason}")
