"""A4 notice for the entrance: QR code to the bot with the building preset.

Neighbours who are not in the house chat (older residents, tenants) scan it
and land in the bot already bound to their building.
"""

from __future__ import annotations

import io

import segno
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from application.ports.documents import Leaflet
from infrastructure.pdf.escalation import FAMILY, FONTS

STEPS = (
    "Наведите камеру телефона на QR-код — откроется бот «Домовой» в MAX.",
    "Опишите проблему своими словами: «в подъезде не горит свет».",
    "Бот оформит заявку в управляющую организацию, назовёт номер и "
    "срок устранения по закону.",
    "О каждом шаге придёт уведомление. Не починили в срок — бот поможет "
    "подготовить жалобу в жилищную инспекцию.",
)


class PdfLeafletRenderer:
    def render(self, leaflet: Leaflet) -> bytes:
        pdf = FPDF(format="A4")
        pdf.set_margins(22, 20, 22)
        pdf.set_auto_page_break(auto=False)
        pdf.add_font(FAMILY, style="", fname=FONTS / "DejaVuSans.ttf")
        pdf.add_font(FAMILY, style="B", fname=FONTS / "DejaVuSans-Bold.ttf")
        pdf.set_title(f"Домовой — {leaflet.address}")
        pdf.add_page()

        _line(pdf, "Сломалось в доме?", size=28, height=13, bold=True)
        _line(
            pdf,
            "Сообщите за минуту — с номером заявки\nи сроком устранения по закону",
            size=16,
            height=8,
        )

        qr = io.BytesIO()
        segno.make(leaflet.link, error="m").save(qr, kind="png", scale=12, border=2)
        qr.seek(0)
        size = 95
        pdf.image(qr, x=(pdf.w - size) / 2, y=pdf.get_y() + 8, w=size, h=size)
        pdf.set_y(pdf.get_y() + size + 12)
        _line(pdf, leaflet.link, size=10, height=5)
        pdf.ln(6)

        pdf.set_font(FAMILY, size=12)
        for number, step in enumerate(STEPS, start=1):
            pdf.multi_cell(
                0, 6.5, f"{number}. {step}", new_x=XPos.LMARGIN, new_y=YPos.NEXT
            )
            pdf.ln(1.5)

        pdf.ln(4)
        _line(pdf, leaflet.address, size=12, height=6.5, bold=True)
        _line(
            pdf,
            f"Управляющая организация: {leaflet.company_name}, "
            f"тел. {leaflet.company_phone}\n"
            "Авария (течёт, искрит, пахнет газом) — звоните в аварийную службу сразу.",
            size=11,
            height=6,
        )
        if leaflet.is_demo:
            pdf.set_y(-18)
            pdf.set_text_color(120, 120, 120)
            _line(
                pdf,
                "Тестовые данные: демонстрационный дом и УО, заявки не передаются "
                "в реальную управляющую организацию.",
                size=8,
                height=4,
            )
        return bytes(pdf.output())


def _line(
    pdf: FPDF, text: str, *, size: float, height: float, bold: bool = False
) -> None:
    pdf.set_font(FAMILY, style="B" if bold else "", size=size)
    pdf.multi_cell(0, height, text, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
