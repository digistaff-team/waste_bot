"""
Сервис генерации документов (PDF): акты, накладные, договоры.
Использует reportlab для создания PDF-файлов.
"""
import os
import logging
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import DOCS_PATH

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Регистрация шрифта с поддержкой кириллицы
# ─────────────────────────────────────────────────────────────────────────────
_FONT_REGISTERED = False

def _ensure_font() -> str:
    """Регистрирует шрифт DejaVu (если доступен) и возвращает его имя."""
    global _FONT_REGISTERED
    font_name = "DejaVu"
    if _FONT_REGISTERED:
        return font_name

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode MS.ttf",
        "DejaVuSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                _FONT_REGISTERED = True
                return font_name
            except Exception:
                pass

    # Fallback — встроенный Helvetica (без кириллицы, но не упадёт)
    logger.warning("Шрифт DejaVu не найден, используется Helvetica (кириллица может не отображаться)")
    return "Helvetica"


def _get_styles(font_name: str) -> dict:
    """Создаёт набор стилей для документа."""
    return {
        "title": ParagraphStyle(
            "title",
            fontName=font_name,
            fontSize=14,
            leading=18,
            alignment=1,  # CENTER
            spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "heading",
            fontName=font_name,
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "normal": ParagraphStyle(
            "normal",
            fontName=font_name,
            fontSize=9,
            leading=12,
        ),
        "small": ParagraphStyle(
            "small",
            fontName=font_name,
            fontSize=8,
            leading=10,
            textColor=colors.grey,
        ),
    }


def _ensure_docs_dir() -> None:
    """Создаёт директорию для документов если не существует."""
    os.makedirs(DOCS_PATH, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Генерация акта приёма-передачи отходов
# ─────────────────────────────────────────────────────────────────────────────

def generate_transfer_act(
    request_id: int,
    lot: dict,
    seller: dict,
    buyer: dict,
    carrier: Optional[dict] = None,
) -> str:
    """
    Генерирует акт приёма-передачи отходов в формате PDF.
    Возвращает путь к созданному файлу.
    """
    _ensure_docs_dir()
    font_name = _ensure_font()
    styles = _get_styles(font_name)

    filename = f"transfer_act_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(DOCS_PATH, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    now_str = datetime.now().strftime("%d.%m.%Y")

    # Заголовок
    story.append(Paragraph("АКТ ПРИЁМА-ПЕРЕДАЧИ ОТХОДОВ", styles["title"]))
    story.append(Paragraph(f"№ {request_id} от {now_str}", styles["title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.4 * cm))

    # Стороны
    story.append(Paragraph("СТОРОНЫ СДЕЛКИ", styles["heading"]))

    parties_data = [
        ["Роль", "Организация", "ИНН", "Контакт"],
        ["Продавец", seller["org_name"], seller["inn"], seller["phone"]],
        ["Покупатель", buyer["org_name"], buyer["inn"], buyer["phone"]],
    ]
    if carrier:
        parties_data.append(["Перевозчик", carrier["org_name"], carrier["inn"], carrier["phone"]])

    parties_table = Table(
        parties_data,
        colWidths=[3 * cm, 6 * cm, 3.5 * cm, 4 * cm],
    )
    parties_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 0.4 * cm))

    # Сведения об отходе
    story.append(Paragraph("СВЕДЕНИЯ ОБ ОТХОДЕ", styles["heading"]))

    waste_data = [
        ["Параметр", "Значение"],
        ["Наименование отхода", lot["fkko_name"]],
        ["Код ФККО", lot["fkko_code"]],
        ["Объём", f"{lot['volume']} {lot['unit']}"],
        ["Цена", f"{lot['price']:,.0f} ₽ {lot['price_format']}"],
        ["Условие передачи", lot["condition"]],
    ]
    if lot.get("address_from"):
        waste_data.append(["Адрес отправки", lot["address_from"]])
    if lot.get("address_to"):
        waste_data.append(["Адрес доставки", lot["address_to"]])

    waste_table = Table(waste_data, colWidths=[5 * cm, 11.6 * cm])
    waste_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(waste_table)
    story.append(Spacer(1, 0.6 * cm))

    # Подписи
    story.append(Paragraph("ПОДПИСИ СТОРОН", styles["heading"]))
    story.append(Spacer(1, 0.3 * cm))

    sig_data = [
        ["Продавец", "Покупатель", "Перевозчик" if carrier else ""],
        [
            f"{seller['org_name']}\n\n_________________",
            f"{buyer['org_name']}\n\n_________________",
            f"{carrier['org_name']}\n\n_________________" if carrier else "",
        ],
    ]
    sig_table = Table(sig_data, colWidths=[5.5 * cm, 5.5 * cm, 5.6 * cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        f"Документ сформирован автоматически системой WasteBot • {now_str}",
        styles["small"],
    ))

    doc.build(story)
    logger.info("Акт приёма-передачи создан: %s", filepath)
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
# Генерация транспортной накладной
# ─────────────────────────────────────────────────────────────────────────────

def generate_waybill(
    request_id: int,
    lot: dict,
    seller: dict,
    buyer: dict,
    carrier: dict,
    distance_km: Optional[float] = None,
    transport_cost: Optional[float] = None,
) -> str:
    """
    Генерирует транспортную накладную в формате PDF.
    Возвращает путь к созданному файлу.
    """
    _ensure_docs_dir()
    font_name = _ensure_font()
    styles = _get_styles(font_name)

    filename = f"waybill_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(DOCS_PATH, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    now_str = datetime.now().strftime("%d.%m.%Y")

    # Заголовок
    story.append(Paragraph("ТРАНСПОРТНАЯ НАКЛАДНАЯ", styles["title"]))
    story.append(Paragraph(f"№ ТН-{request_id} от {now_str}", styles["title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.4 * cm))

    # Грузоотправитель / Грузополучатель
    story.append(Paragraph("УЧАСТНИКИ ПЕРЕВОЗКИ", styles["heading"]))

    parties_data = [
        ["", "Организация", "ИНН", "Телефон", "Email"],
        ["Грузоотправитель", seller["org_name"], seller["inn"], seller["phone"], seller["email"]],
        ["Грузополучатель", buyer["org_name"], buyer["inn"], buyer["phone"], buyer["email"]],
        ["Перевозчик", carrier["org_name"], carrier["inn"], carrier["phone"], carrier["email"]],
    ]
    parties_table = Table(
        parties_data,
        colWidths=[3.5 * cm, 5 * cm, 3 * cm, 3 * cm, 3.1 * cm],
    )
    parties_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EBF5FB")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 0.4 * cm))

    # Маршрут
    story.append(Paragraph("МАРШРУТ И ГРУЗ", styles["heading"]))

    route_data = [
        ["Параметр", "Значение"],
        ["Пункт отправления", lot.get("address_from", "—")],
        ["Пункт назначения", lot.get("address_to", "—")],
        ["Расстояние", f"{distance_km} км" if distance_km else "—"],
        ["Наименование груза", lot["fkko_name"]],
        ["Код ФККО", lot["fkko_code"]],
        ["Масса/объём груза", f"{lot['volume']} {lot['unit']}"],
        ["Стоимость перевозки", f"{transport_cost:,.0f} ₽" if transport_cost else "—"],
    ]
    if carrier.get("vehicle_types"):
        route_data.append(["Тип транспортного средства", carrier["vehicle_types"]])

    route_table = Table(route_data, colWidths=[5.5 * cm, 11.1 * cm])
    route_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EBF5FB")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(route_table)
    story.append(Spacer(1, 0.6 * cm))

    # Отметки о приёме/сдаче
    story.append(Paragraph("ОТМЕТКИ О ПРИЁМЕ И СДАЧЕ ГРУЗА", styles["heading"]))
    story.append(Spacer(1, 0.2 * cm))

    marks_data = [
        ["Принял (Перевозчик)", "Сдал (Грузоотправитель)", "Получил (Грузополучатель)"],
        [
            f"{carrier['org_name']}\nДата: ___________\nПодпись: _________",
            f"{seller['org_name']}\nДата: ___________\nПодпись: _________",
            f"{buyer['org_name']}\nДата: ___________\nПодпись: _________",
        ],
    ]
    marks_table = Table(marks_data, colWidths=[5.5 * cm, 5.5 * cm, 5.6 * cm])
    marks_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6EAF8")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 16),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 16),
    ]))
    story.append(marks_table)

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        f"Документ сформирован автоматически системой WasteBot • {now_str}",
        styles["small"],
    ))

    doc.build(story)
    logger.info("Транспортная накладная создана: %s", filepath)
    return filepath
