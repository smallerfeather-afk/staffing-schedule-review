"""Render a populated Excel schedule template as a one-page PDF."""

from dataclasses import dataclass
from io import BytesIO
import re
from xml.etree import ElementTree

from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.styles.colors import COLOR_INDEX
from openpyxl.utils import get_column_letter
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import TABLOID, landscape
from reportlab.pdfgen.canvas import Canvas

PAGE_SIZE = landscape(TABLOID)
PAGE_MARGIN = 7.2
DEFAULT_FONT_SIZE = 11.0
DEFAULT_ROW_HEIGHT = 15.0
DEFAULT_COLUMN_WIDTH = 8.43
GRID_COLOR = HexColor("#454545")


class TemplatePDFError(ValueError):
    """Raised when an Excel template cannot be rendered safely."""


@dataclass(frozen=True)
class _TextRun:
    text: str
    size: float
    bold: bool
    color: Color


def _theme_colors(workbook: object) -> dict[int, str]:
    theme = getattr(workbook, "loaded_theme", None)
    if not theme:
        return {}
    try:
        root = ElementTree.fromstring(theme)
    except ElementTree.ParseError:
        return {}
    namespace = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    scheme = root.find(".//a:themeElements/a:clrScheme", namespace)
    if scheme is None:
        return {}

    theme_indexes = {
        "lt1": 0,
        "dk1": 1,
        "lt2": 2,
        "dk2": 3,
        "accent1": 4,
        "accent2": 5,
        "accent3": 6,
        "accent4": 7,
        "accent5": 8,
        "accent6": 9,
        "hlink": 10,
        "folHlink": 11,
    }
    palette: dict[int, str] = {}
    for entry in list(scheme):
        tag = entry.tag.rsplit("}", 1)[-1]
        index = theme_indexes.get(tag)
        if index is None:
            continue
        color_node = next(iter(entry), None)
        if color_node is None:
            continue
        value = color_node.attrib.get("val")
        if not value or not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            value = color_node.attrib.get("lastClr")
        if value and re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            palette[index] = value
    return palette


def _apply_tint(value: str, tint: float) -> str:
    channels = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
    if tint < 0:
        channels = [round(channel * (1 + tint)) for channel in channels]
    elif tint > 0:
        channels = [
            round(channel + ((255 - channel) * tint))
            for channel in channels
        ]
    return "".join(f"{max(0, min(255, channel)):02X}" for channel in channels)


def _excel_color(
    color: object,
    default: Color,
    theme_colors: dict[int, str],
) -> Color:
    color_type = getattr(color, "type", None)
    value: str | None = None
    if color_type == "rgb":
        value = getattr(color, "rgb", None)
    elif color_type == "indexed":
        index = getattr(color, "indexed", None)
        if isinstance(index, int) and 0 <= index < len(COLOR_INDEX):
            value = COLOR_INDEX[index]
    elif color_type == "theme":
        index = getattr(color, "theme", None)
        if isinstance(index, int):
            value = theme_colors.get(index)
    if not value or not re.fullmatch(r"[0-9A-Fa-f]{6,8}", value):
        return default
    tint = getattr(color, "tint", 0.0)
    if isinstance(tint, (int, float)) and tint:
        value = _apply_tint(value[-6:], float(tint))
    return HexColor(f"#{value[-6:]}")


def _column_points(width: float | None) -> float:
    excel_width = width if width is not None else DEFAULT_COLUMN_WIDTH
    pixels = (excel_width * 12) if excel_width <= 1 else (excel_width * 7 + 5)
    return pixels * 0.75


def _font_properties(
    font: object,
    *,
    fallback_size: float,
    fallback_color: Color,
    theme_colors: dict[int, str],
) -> tuple[float, bool, Color]:
    size = float(getattr(font, "sz", None) or fallback_size)
    bold = bool(getattr(font, "b", None) or getattr(font, "bold", None))
    color = _excel_color(
        getattr(font, "color", None),
        fallback_color,
        theme_colors,
    )
    return size, bold, color


def _append_text(
    lines: list[list[_TextRun]],
    text: str,
    *,
    size: float,
    bold: bool,
    color: Color,
) -> None:
    parts = re.split(r"(\n)", text)
    for part in parts:
        if part == "\n":
            lines.append([])
        elif part:
            lines[-1].append(_TextRun(part, size, bold, color))


def _text_lines(
    cell: object,
    *,
    fallback_color: Color,
    theme_colors: dict[int, str],
) -> list[list[_TextRun]]:
    value = cell.value
    if value is None:
        return []

    cell_size, cell_bold, cell_color = _font_properties(
        cell.font,
        fallback_size=DEFAULT_FONT_SIZE,
        fallback_color=fallback_color,
        theme_colors=theme_colors,
    )
    lines: list[list[_TextRun]] = [[]]
    if isinstance(value, CellRichText):
        for item in value:
            if isinstance(item, TextBlock):
                size, bold, color = _font_properties(
                    item.font,
                    fallback_size=cell_size,
                    fallback_color=cell_color,
                    theme_colors=theme_colors,
                )
                text = item.text
            else:
                size, bold, color = cell_size, cell_bold, cell_color
                text = str(item)
            _append_text(
                lines,
                text,
                size=size,
                bold=bold,
                color=color,
            )
    else:
        _append_text(
            lines,
            str(value),
            size=cell_size,
            bold=cell_bold,
            color=cell_color,
        )
    return lines


def _font_name(run: _TextRun) -> str:
    return "Helvetica-Bold" if run.bold else "Helvetica"


def _line_width(canvas: Canvas, line: list[_TextRun], scale: float) -> float:
    return sum(
        canvas.stringWidth(run.text, _font_name(run), run.size * scale)
        for run in line
    )


def _draw_text(
    canvas: Canvas,
    cell: object,
    x: float,
    y: float,
    width: float,
    height: float,
    scale: float,
    *,
    fallback_color: Color,
    theme_colors: dict[int, str],
) -> None:
    lines = _text_lines(
        cell,
        fallback_color=fallback_color,
        theme_colors=theme_colors,
    )
    if not lines:
        return

    padding = max(0.7, 2.0 * scale)
    available_width = max(1.0, width - (padding * 2))
    available_height = max(1.0, height - (padding * 2))
    widest = max(_line_width(canvas, line, scale) for line in lines)
    largest_size = max(
        (run.size for line in lines for run in line),
        default=DEFAULT_FONT_SIZE,
    )
    line_height = largest_size * scale * 1.12
    fit = min(
        1.0,
        available_width / widest if widest else 1.0,
        available_height / (line_height * len(lines)),
    )
    text_scale = scale * fit
    line_height = largest_size * text_scale * 1.12
    block_height = line_height * len(lines)
    baseline = y + ((height + block_height) / 2) - line_height
    horizontal = getattr(cell.alignment, "horizontal", None)

    for line in lines:
        line_width = _line_width(canvas, line, text_scale)
        if horizontal == "left":
            cursor = x + padding
        elif horizontal == "right":
            cursor = x + width - padding - line_width
        else:
            cursor = x + ((width - line_width) / 2)

        for run in line:
            font_size = max(2.5, run.size * text_scale)
            canvas.setFont(_font_name(run), font_size)
            canvas.setFillColor(run.color)
            canvas.drawString(cursor, baseline, run.text)
            cursor += canvas.stringWidth(
                run.text,
                _font_name(run),
                font_size,
            )
        baseline -= line_height


def _render_section(
    canvas: Canvas,
    worksheet: object,
    *,
    theme_colors: dict[int, str],
    column_widths: list[float],
    max_column: int,
    row_start: int,
    row_end: int,
    merged_anchors: dict[tuple[int, int], tuple[int, int]],
    merged_children: set[tuple[int, int]],
) -> None:
    row_heights = {
        row: worksheet.row_dimensions[row].height or DEFAULT_ROW_HEIGHT
        for row in range(row_start, row_end + 1)
    }
    total_width = sum(column_widths)
    total_height = sum(row_heights.values())
    page_width, page_height = PAGE_SIZE
    available_width = page_width - (PAGE_MARGIN * 2)
    available_height = page_height - (PAGE_MARGIN * 2)
    scale = min(available_width / total_width, available_height / total_height)
    render_width = total_width * scale
    render_height = total_height * scale
    origin_x = (page_width - render_width) / 2
    top_y = (page_height + render_height) / 2

    column_x = [origin_x]
    for width in column_widths:
        column_x.append(column_x[-1] + (width * scale))
    row_edges = {row_start: top_y}
    current_y = top_y
    for row in range(row_start, row_end + 1):
        current_y -= row_heights[row] * scale
        row_edges[row + 1] = current_y

    for row in range(row_start, row_end + 1):
        for column in range(1, max_column + 1):
            if (row, column) in merged_children:
                continue
            end_row, end_column = merged_anchors.get(
                (row, column),
                (row, column),
            )
            if end_row > row_end:
                raise TemplatePDFError(
                    "A merged template cell crosses a PDF page boundary."
                )
            x = column_x[column - 1]
            cell_top = row_edges[row]
            width = column_x[end_column] - x
            y = row_edges[end_row + 1]
            height = cell_top - y
            cell = worksheet.cell(row, column)

            fill_color = HexColor("#FFFFFF")
            if getattr(cell.fill, "fill_type", None) == "solid":
                fill_color = _excel_color(
                    cell.fill.fgColor,
                    fill_color,
                    theme_colors,
                )
            canvas.setFillColor(fill_color)
            canvas.setStrokeColor(GRID_COLOR)
            canvas.setLineWidth(0.35)
            canvas.rect(x, y, width, height, stroke=1, fill=1)
            luminance = (
                (fill_color.red * 0.2126)
                + (fill_color.green * 0.7152)
                + (fill_color.blue * 0.0722)
            )
            fallback_color = (
                HexColor("#FFFFFF")
                if luminance < 0.42
                else HexColor("#000000")
            )
            _draw_text(
                canvas,
                cell,
                x,
                y,
                width,
                height,
                scale,
                fallback_color=fallback_color,
                theme_colors=theme_colors,
            )


def export_template_pdf(
    workbook_bytes: bytes,
    *,
    department: str,
) -> bytes:
    """Return a landscape PDF of a populated operational template."""
    try:
        workbook = load_workbook(BytesIO(workbook_bytes), rich_text=True)
    except Exception as exc:
        raise TemplatePDFError(
            "The populated Excel template could not be opened for PDF export."
        ) from exc

    worksheet = workbook.worksheets[0]
    theme_colors = _theme_colors(workbook)
    max_row = worksheet.max_row
    max_column = worksheet.max_column
    if max_row < 1 or max_column < 1:
        raise TemplatePDFError("The populated template is empty.")

    column_widths = [
        _column_points(
            worksheet.column_dimensions[get_column_letter(column)].width
        )
        for column in range(1, max_column + 1)
    ]
    merged_anchors: dict[tuple[int, int], tuple[int, int]] = {}
    merged_children: set[tuple[int, int]] = set()
    for merged_range in worksheet.merged_cells.ranges:
        anchor = (merged_range.min_row, merged_range.min_col)
        merged_anchors[anchor] = (
            merged_range.max_row,
            merged_range.max_col,
        )
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for column in range(
                merged_range.min_col,
                merged_range.max_col + 1,
            ):
                if (row, column) != anchor:
                    merged_children.add((row, column))

    output = BytesIO()
    canvas = Canvas(output, pagesize=PAGE_SIZE, pageCompression=1)
    canvas.setTitle(f"2 Week Outlook - {department}")
    canvas.setAuthor("2 week schedule generator")

    department_key = re.sub(r"[^a-z0-9]+", "", department.casefold())
    if department_key == "almc" and max_row >= 39:
        sections = ((1, 21), (23, 39))
    else:
        sections = ((1, max_row),)

    for row_start, row_end in sections:
        _render_section(
            canvas,
            worksheet,
            theme_colors=theme_colors,
            column_widths=column_widths,
            max_column=max_column,
            row_start=row_start,
            row_end=row_end,
            merged_anchors=merged_anchors,
            merged_children=merged_children,
        )
        canvas.showPage()

    canvas.save()
    return output.getvalue()
