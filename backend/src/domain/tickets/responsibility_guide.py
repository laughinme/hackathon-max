"""Who answers for what around a building, and where to turn.

The bot files tickets only to the managing company; this guide covers the
rest, so a resident is not bounced between organisations. Sources are the
same as in docs/DATA.md §3; they are checked against the texts with the SLA
table (DECISIONS Q-13).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.tickets.enums import ResponsibleParty


@dataclass(frozen=True, slots=True)
class GuideEntry:
    emoji: str
    situation: str
    party: ResponsibleParty | None
    who: str
    basis: str
    where: str


GUIDE: tuple[GuideEntry, ...] = (
    GuideEntry(
        "🏢",
        "Подъезд, лифт, крыша, подвал, стояки до первого крана в квартире, "
        "придомовая территория",
        ResponsibleParty.MANAGEMENT_COMPANY,
        "Управляющая организация или ТСЖ",
        "ЖК РФ ст. 161; ПП РФ № 491",
        "заявка через «Домового»",
    ),
    GuideEntry(
        "🚰",
        "Внутри квартиры после первого крана: смеситель, розетка, батарея "
        "с отсекающим краном",
        ResponsibleParty.OWNER,
        "Собственник квартиры",
        "ПП РФ № 491, п. 5",
        "свой мастер или платная услуга УО",
    ),
    GuideEntry(
        "💧",
        "Нет воды, тепла или света во всём доме из-за сетей, плохое качество ресурса",
        ResponsibleParty.RESOURCE_SUPPLIER,
        "Ресурсоснабжающая организация",
        "ПП РФ № 354",
        "заявка через «Домового»: УО и аварийная служба передадут дальше",
    ),
    GuideEntry(
        "🏗",
        "Капитальный ремонт крыши, фасада, лифтов по региональной программе",
        ResponsibleParty.CAPITAL_REPAIR_OPERATOR,
        "Региональный оператор капремонта",
        "ЖК РФ, раздел IX",
        "сайт регоператора или Госуслуги",
    ),
    GuideEntry(
        "🗑",
        "Вывоз мусора с контейнерной площадки",
        None,
        "Региональный оператор по обращению с ТКО",
        "89-ФЗ «Об отходах производства и потребления»",
        "горячая линия регоператора ТКО",
    ),
    GuideEntry(
        "🛣",
        "Дороги, тротуары и уличное освещение за границей участка дома",
        ResponsibleParty.MUNICIPALITY,
        "Администрация муниципалитета",
        "131-ФЗ",
        "Госуслуги, «Решаем вместе»",
    ),
    GuideEntry(
        "⚖️",
        "УО не выполняет заявку в нормативный срок",
        None,
        "Государственная жилищная инспекция региона",
        "ЖК РФ ст. 20",
        "«Домовой» подготовит жалобу с историей заявки",
    ),
)
