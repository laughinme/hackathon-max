"""Photos in MAX messages: read them from updates, send them back by token."""

from __future__ import annotations

from typing import Any, Literal

from maxapi.enums.attachment import AttachmentType
from pydantic import BaseModel

from domain.tickets.entities import MAX_PHOTOS, TicketPhoto


def message_photos(event: Any) -> list[TicketPhoto]:
    """Image attachments of an incoming message (MAX keeps them by token)."""

    message = getattr(event, "message", None)
    body = getattr(message, "body", None)
    photos = []
    for attachment in getattr(body, "attachments", None) or []:
        if getattr(attachment, "type", None) != AttachmentType.IMAGE:
            continue
        payload = attachment.payload
        token = getattr(payload, "token", None)
        url = getattr(payload, "url", None)
        if token and url:
            photos.append(TicketPhoto(token=token, url=url))
    return photos[:MAX_PHOTOS]


class _TokenPayload(BaseModel):
    token: str


class PhotoByToken(BaseModel):
    """`{"type": "image", "payload": {"token": ...}}` — MAX PhotoAttachmentRequest
    with only the token (its fields are mutually exclusive). maxapi sends any
    attachment through `model_dump()`."""

    type: Literal["image"] = "image"
    payload: _TokenPayload


def photo_attachments(
    photos: tuple[TicketPhoto, ...] | list[TicketPhoto],
) -> list[PhotoByToken]:
    return [PhotoByToken(payload=_TokenPayload(token=photo.token)) for photo in photos]


def to_dicts(photos: list[TicketPhoto]) -> list[dict[str, str]]:
    return [{"token": p.token, "url": p.url} for p in photos]


def from_dicts(raw: list[dict[str, str]] | None) -> list[TicketPhoto]:
    return [TicketPhoto(**item) for item in raw or []]
