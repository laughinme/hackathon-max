from maxapi.enums.attachment import AttachmentType
from maxapi.enums.chat_type import ChatType
from maxapi.types.attachments.attachment import PhotoAttachmentPayload
from maxapi.types.attachments.image import Image
from maxapi.types.message import Message, MessageBody, Recipient
from maxapi.types.updates.message_created import MessageCreated

from application.chats.file_from_chat import FileFromChatCommand
from application.chats.spot_complaint import NewProblem
from bot.media import message_photos, photo_attachments
from domain.tickets.entities import MAX_PHOTOS, TicketPhoto
from tests.fakes import make_world
from tests.unit.domain.test_ticket import make_ticket


def _photo(n: int) -> TicketPhoto:
    return TicketPhoto(token=f"tok-{n}", url=f"https://i.max.ru/{n}.jpg")


def test_ticket_keeps_up_to_five_distinct_photos():
    ticket = make_ticket()
    ticket.attach_photos([_photo(1), _photo(1), *[_photo(n) for n in range(2, 9)]])
    assert [p.token for p in ticket.photos] == [f"tok-{n}" for n in range(1, 6)]
    assert len(ticket.photos) == MAX_PHOTOS


def _message_with_photo(text: str | None) -> MessageCreated:
    image = Image(
        type=AttachmentType.IMAGE,
        payload=PhotoAttachmentPayload(photo_id=1, token="tok-1", url="https://i/1"),
    )
    message = Message(
        recipient=Recipient(chat_id=1, chat_type=ChatType.DIALOG),
        timestamp=0,
        body=MessageBody(mid="m", seq=0, text=text, attachments=[image]),
    )
    return MessageCreated(timestamp=0, message=message)


def test_photos_are_read_from_an_incoming_message():
    assert message_photos(_message_with_photo("течёт")) == [
        TicketPhoto(token="tok-1", url="https://i/1")
    ]


def test_photos_are_sent_back_by_token_only():
    [attachment] = photo_attachments([_photo(1)])
    dumped = attachment.model_dump()
    assert dumped == {"type": "image", "payload": {"token": "tok-1"}}


async def test_photo_from_the_house_chat_lands_in_the_ticket():
    world = make_world()
    await world.services.register_chat.execute(-700, 11)
    await world.services.bind_chat.execute(-700, "psk001", 11)
    spotted = await world.services.spot_complaint.execute(
        -700, 11, "m.1", "Опять течёт труба в подвале", (_photo(1),)
    )
    assert isinstance(spotted, NewProblem)
    ticket = await world.services.file_from_chat.execute(
        FileFromChatCommand(spotted.hint.id, 12, card_mid="c")
    )
    assert ticket.photos == (_photo(1),)
