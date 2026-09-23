"""The complaint to the housing inspection as a PDF (fpdf2, DejaVu fonts).

Facts only, taken from the ticket: what was reported, when, the legal deadline
with its basis, and the timeline. The applicant's name and postal address are
left blank on purpose: the service does not collect them, and the inspection
needs them to answer (59-FZ, art. 7). Legal references here must be checked
against the source texts together with the SLA table (DECISIONS Q-13).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from application.ports.documents import EscalationDocument
from application.tickets.dto import TicketView
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus

FONTS = Path(__file__).parent / "fonts"
FAMILY = "DejaVu"
TIMEZONE = ZoneInfo("Europe/Moscow")

STATUS_TEXT: dict[TicketStatus, str] = {
    TicketStatus.REGISTERED: "Зарегистрирована",
    TicketStatus.ACKNOWLEDGED: "Принята управляющей организацией",
    TicketStatus.IN_PROGRESS: "В работе",
    TicketStatus.DONE: "Отмечена выполненной",
    TicketStatus.CONFIRMED: "Закрыта",
    TicketStatus.REJECTED: "Отклонена",
}

ACTOR_TEXT: dict[ActorRole, str] = {
    ActorRole.RESIDENT: "заявитель",
    ActorRole.DISPATCHER: "управляющая организация",
    ActorRole.SYSTEM: "система",
}

PARTY_TEXT: dict[ResponsibleParty, str] = {
    ResponsibleParty.MANAGEMENT_COMPANY: "управляющая организация",
    ResponsibleParty.RESOURCE_SUPPLIER: "ресурсоснабжающая организация",
    ResponsibleParty.CAPITAL_REPAIR_OPERATOR: "региональный оператор капремонта",
    ResponsibleParty.MUNICIPALITY: "администрация муниципалитета",
    ResponsibleParty.OWNER: "собственник помещения",
}

LEGAL_GROUNDS = (
    "Управляющая организация отвечает перед собственниками помещений за оказание "
    "услуг и выполнение работ по надлежащему содержанию общего имущества "
    "(ч. 2.3 ст. 161 Жилищного кодекса РФ). Порядок приёма и исполнения заявок "
    "установлен Правилами осуществления деятельности по управлению "
    "многоквартирными домами, утверждёнными постановлением Правительства РФ "
    "от 15.05.2013 № 416. Контроль за соблюдением этих требований — предмет "
    "государственного жилищного надзора (ст. 20 Жилищного кодекса РФ)."
)


def moment(value: datetime) -> str:
    return value.astimezone(TIMEZONE).strftime("%d.%m.%Y %H:%M")


def overdue_by(delta: timedelta) -> str:
    hours = max(1, int(delta.total_seconds() // 3600))
    days, rest = divmod(hours, 24)
    if days == 0:
        return f"{hours} ч"
    return f"{days} сут. {rest} ч" if rest else f"{days} сут."


class PdfEscalationRenderer:
    def render(self, document: EscalationDocument) -> bytes:
        pdf = FPDF(format="A4")
        pdf.set_margins(20, 18, 20)
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_font(FAMILY, style="", fname=FONTS / "DejaVuSans.ttf")
        pdf.add_font(FAMILY, style="B", fname=FONTS / "DejaVuSans-Bold.ttf")
        pdf.set_title(f"Жалоба по заявке № {document.ticket.number}")
        pdf.add_page()

        _addressee(pdf, document)
        _title(pdf)
        _facts(pdf, document)
        _history(pdf, document.ticket)
        _requests(pdf, document.ticket)
        _signature(pdf)
        _footer(pdf, document)
        return bytes(pdf.output())


def _paragraph(
    pdf: FPDF, text: str, *, size: float = 10, bold: bool = False, align: str = "J"
) -> None:
    pdf.set_font(FAMILY, style="B" if bold else "", size=size)
    pdf.multi_cell(
        0, size * 0.5, text, align=align, new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )


def _addressee(pdf: FPDF, document: EscalationDocument) -> None:
    left = pdf.l_margin
    pdf.set_left_margin(pdf.w / 2)
    pdf.set_x(pdf.w / 2)
    _paragraph(
        pdf,
        f"В орган государственного жилищного надзора\n{document.region}\n\n"
        "от: ____________________________\n"
        "   (фамилия, имя, отчество)\n"
        "адрес для ответа: ______________\n"
        "________________________________\n"
        "телефон / e-mail: _______________",
        size=9.5,
        align="L",
    )
    pdf.set_left_margin(left)
    pdf.ln(5)


def _title(pdf: FPDF) -> None:
    pdf.set_font(FAMILY, style="B", size=12)
    pdf.multi_cell(
        0,
        6,
        "ЖАЛОБА\nна нарушение управляющей организацией срока устранения неисправности",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)


def _facts(pdf: FPDF, document: EscalationDocument) -> None:
    ticket = document.ticket
    urgency = "аварийная" if ticket.is_emergency else "неаварийная"
    react = (
        f" Срок реакции аварийной службы — до {moment(ticket.react_by)}."
        if ticket.react_by
        else ""
    )
    _paragraph(
        pdf,
        f"{moment(ticket.created_at)} я подал(а) в управляющую организацию "
        f"{document.company_name} (тел. {document.company_phone}) заявку "
        f"№ {ticket.number} по адресу: {ticket.building_address}.",
    )
    pdf.ln(1)
    summary = ticket.description.rstrip(".")
    _paragraph(pdf, f"Суть обращения: «{summary}». Заявка {urgency}.")
    pdf.ln(1)
    _paragraph(
        pdf,
        f"Нормативный срок устранения — до {moment(ticket.resolve_by)} "
        f"({ticket.deadline_basis}).{react} Ответственный: "
        f"{PARTY_TEXT[ticket.responsible_party]} ({ticket.responsibility_basis}).",
    )
    pdf.ln(1)
    _paragraph(
        pdf,
        f"На {moment(document.generated_at)} срок истёк "
        f"{overdue_by(document.generated_at - ticket.resolve_by)} назад, "
        f"неисправность не устранена. Текущий статус заявки: "
        f"«{STATUS_TEXT[ticket.status]}».",
        bold=True,
    )
    pdf.ln(1)
    _paragraph(pdf, LEGAL_GROUNDS)
    pdf.ln(3)


def _history(pdf: FPDF, ticket: TicketView) -> None:
    _paragraph(pdf, "История заявки", bold=True)
    pdf.ln(1)
    pdf.set_font(FAMILY, size=8.5)
    with pdf.table(
        col_widths=(33, 42, 34, 61),
        text_align="LEFT",
        line_height=4.4,
        first_row_as_headings=True,
    ) as table:
        table.row(("Дата и время", "Статус", "Кто", "Комментарий"))
        for event in ticket.events:
            table.row(
                (
                    moment(event.at),
                    STATUS_TEXT[event.status],
                    ACTOR_TEXT[event.actor_role],
                    event.comment or "—",
                )
            )
    pdf.ln(4)


def _requests(pdf: FPDF, ticket: TicketView) -> None:
    _paragraph(pdf, "Прошу:", bold=True)
    _paragraph(
        pdf,
        f"1. Провести проверку исполнения управляющей организацией обязанностей "
        f"по заявке № {ticket.number}.\n"
        "2. Принять меры к устранению нарушения.\n"
        "3. О результатах рассмотрения сообщить мне в срок, установленный "
        "ст. 12 Федерального закона от 02.05.2006 № 59-ФЗ «О порядке "
        "рассмотрения обращений граждан Российской Федерации».",
    )
    pdf.ln(6)


def _signature(pdf: FPDF) -> None:
    _paragraph(
        pdf, "Дата: «____» ______________ 20___ г.        Подпись: ______________"
    )
    pdf.ln(4)


def _footer(pdf: FPDF, document: EscalationDocument) -> None:
    note = (
        f"Документ подготовлен сервисом «Домовой» {moment(document.generated_at)} "
        "по данным заявки. Проверьте текст, впишите свои данные, подпишите и "
        "подайте в жилищную инспекцию вашего региона лично, почтой или через её "
        "электронную приёмную."
    )
    if document.is_demo:
        note += " ТЕСТОВЫЕ ДАННЫЕ: заявка демонстрационная, документ не для подачи."
    pdf.set_text_color(110, 110, 110)
    _paragraph(pdf, note, size=7.5)
    pdf.set_text_color(0, 0, 0)
