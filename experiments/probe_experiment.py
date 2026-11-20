"""Compare separate chaining and linear probing across load factors."""

import csv
import math
import random
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from zlib import compress

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(ROOT_DIRECTORY))

from experiments.chaining_probe_experiment import (
    ChainingResult,
    make_svg as make_chaining_svg,
    measure as measure_chaining,
    write_csv as write_chaining_csv,
)
from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable

CAPACITY = 4093
FIRST_LOAD_FACTOR_STEP = 1
LAST_LOAD_FACTOR_STEP = 9
FAILURE_QUERY_COUNT = CAPACITY
RANDOM_SEED = 20261120

CSV_FIELDS = (
    "target_alpha",
    "actual_alpha",
    "item_count",
    "chaining_successful_avg_probes",
    "chaining_successful_theory",
    "chaining_unsuccessful_avg_probes",
    "chaining_unsuccessful_theory",
    "linear_successful_avg_probes",
    "linear_successful_theory",
    "linear_unsuccessful_avg_probes",
    "linear_unsuccessful_theory",
)


@dataclass(frozen=True)
class ExperimentResult:
    target_alpha: float
    actual_alpha: float
    item_count: int
    chaining_successful_avg_probes: float
    chaining_successful_theory: float
    chaining_unsuccessful_avg_probes: float
    chaining_unsuccessful_theory: float
    linear_successful_avg_probes: float
    linear_successful_theory: float
    linear_unsuccessful_avg_probes: float
    linear_unsuccessful_theory: float


def random_urls(
    generator: random.Random, namespace: str, count: int
) -> list[str]:
    return [
        f"https://{namespace}.example/{generator.getrandbits(128):032x}-{index}"
        for index in range(count)
    ]


def measure() -> list[ExperimentResult]:
    generator = random.Random(RANDOM_SEED)
    maximum_item_count = round(CAPACITY * LAST_LOAD_FACTOR_STEP / 10)
    keys = random_urls(generator, "stored", maximum_item_count)
    missing_keys = random_urls(generator, "missing", FAILURE_QUERY_COUNT)
    results = []

    for step in range(FIRST_LOAD_FACTOR_STEP, LAST_LOAD_FACTOR_STEP + 1):
        target_alpha = step / 10
        item_count = round(CAPACITY * target_alpha)
        chaining: HashTable[str] = HashTable(capacity=CAPACITY, max_load=None)
        linear: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=CAPACITY, max_load=None
        )
        for key in keys[:item_count]:
            chaining.put(key, key)
            linear.put(key, key)

        actual_alpha = item_count / CAPACITY
        chaining_successful = sum(
            chaining.probe_count(key) for key in keys[:item_count]
        ) / item_count
        chaining_unsuccessful = sum(
            chaining.probe_count(key) for key in missing_keys
        ) / len(missing_keys)
        linear_successful = sum(
            linear.probe_count(key) for key in keys[:item_count]
        ) / item_count
        linear_unsuccessful = sum(
            linear.probe_count(key) for key in missing_keys
        ) / len(missing_keys)

        results.append(
            ExperimentResult(
                target_alpha=target_alpha,
                actual_alpha=actual_alpha,
                item_count=item_count,
                chaining_successful_avg_probes=chaining_successful,
                chaining_successful_theory=1 + actual_alpha / 2,
                chaining_unsuccessful_avg_probes=chaining_unsuccessful,
                chaining_unsuccessful_theory=actual_alpha,
                linear_successful_avg_probes=linear_successful,
                linear_successful_theory=0.5
                * (1 + 1 / (1 - actual_alpha)),
                linear_unsuccessful_avg_probes=linear_unsuccessful,
                linear_unsuccessful_theory=0.5
                * (1 + 1 / (1 - actual_alpha) ** 2),
            )
        )

    return results


def write_csv(results: list[ExperimentResult], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output, fieldnames=CSV_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for result in results:
            row = {
                "target_alpha": f"{result.target_alpha:.1f}",
                "actual_alpha": f"{result.actual_alpha:.6f}",
                "item_count": result.item_count,
            }
            for field in CSV_FIELDS[3:]:
                row[field] = f"{getattr(result, field):.6f}"
            writer.writerow(row)


def make_svg(results: list[ExperimentResult]) -> str:
    width, height = 1100, 620
    panel_width, panel_gap = 490, 44
    panel_top, panel_bottom = 90, 530
    panel_lefts = (42, 42 + panel_width + panel_gap)
    panels = (
        (
            "체이닝",
            "chaining_successful_avg_probes",
            "chaining_successful_theory",
            "chaining_unsuccessful_avg_probes",
            "chaining_unsuccessful_theory",
        ),
        (
            "선형 탐지",
            "linear_successful_avg_probes",
            "linear_successful_theory",
            "linear_unsuccessful_avg_probes",
            "linear_unsuccessful_theory",
        ),
    )
    colors = ("#1769aa", "#d05a00")
    series_labels = (
        "성공 측정",
        "성공 이론",
        "실패 측정",
        "실패 이론",
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>체이닝과 선형 탐지의 탐색 비용</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#222">',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-size="21">적재율에 따른 해시 테이블 탐색 비용</text>',
    ]
    for panel_index, panel in enumerate(panels):
        (
            title,
            successful_measured,
            successful_theory,
            unsuccessful_measured,
            unsuccessful_theory,
        ) = panel
        left = panel_lefts[panel_index]
        plot_left = left + 55
        plot_right = left + panel_width - 16
        plot_top = panel_top + 20
        plot_bottom = panel_bottom - 60
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top
        maximum = max(
            getattr(result, field)
            for result in results
            for field in (
                successful_measured,
                successful_theory,
                unsuccessful_measured,
                unsuccessful_theory,
            )
        )
        tick_step = 1 if maximum < 10 else 10
        y_max = math.ceil(maximum * 1.08 / tick_step) * tick_step

        def x_position(alpha: float) -> float:
            return plot_left + (alpha - 0.1) / 0.8 * plot_width

        def y_position(value: float) -> float:
            return plot_top + (y_max - value) / y_max * plot_height

        parts.append(
            f'<text x="{left + panel_width / 2}" y="{panel_top}" text-anchor="middle" font-size="17">{title}</text>'
        )
        for tick in range(0, y_max + 1, tick_step):
            y = y_position(float(tick))
            parts.append(
                f'<line x1="{plot_left}" y1="{y:.2f}" x2="{plot_right}" y2="{y:.2f}" stroke="#ddd"/>'
            )
            parts.append(
                f'<text x="{plot_left - 10}" y="{y + 4:.2f}" text-anchor="end">{tick}</text>'
            )
        for tick in range(1, 10, 2):
            alpha = tick / 10
            x = x_position(alpha)
            parts.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_bottom}" stroke="#eee"/>'
            )
            parts.append(
                f'<text x="{x:.2f}" y="{plot_bottom + 20}" text-anchor="middle">{alpha:.1f}</text>'
            )
        parts.extend(
            [
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" stroke="#333"/>',
                f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_bottom}" stroke="#333"/>',
                f'<text x="{plot_left + plot_width / 2}" y="{panel_bottom - 10}" text-anchor="middle">적재율 α</text>',
            ]
        )
        fields = (
            successful_measured,
            successful_theory,
            unsuccessful_measured,
            unsuccessful_theory,
        )
        for series_index, field in enumerate(fields):
            color = colors[series_index // 2]
            dash = series_index % 2 == 1
            points = " ".join(
                f"{x_position(result.actual_alpha):.2f},{y_position(getattr(result, field)):.2f}"
                for result in results
            )
            dash_attribute = ' stroke-dasharray="7 5"' if dash else ""
            parts.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash_attribute}/>'
            )
            for result in results:
                parts.append(
                    f'<circle cx="{x_position(result.actual_alpha):.2f}" cy="{y_position(getattr(result, field)):.2f}" r="2.5" fill="{color}"/>'
                )
            legend_x = left + 30 + series_index % 2 * 220
            legend_y = panel_top + 30 + series_index // 2 * 22
            parts.append(
                f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 23}" y2="{legend_y}" stroke="{color}" stroke-width="2"{dash_attribute}/>'
            )
            parts.append(
                f'<text x="{legend_x + 29}" y="{legend_y + 4}">{series_labels[series_index]}</text>'
            )
    parts.extend(
        [
            f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle">동일 URL 키, 테이블 용량 {CAPACITY}; 점선은 이론값</text>',
            "</g>",
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def _font_tables(font: bytes) -> dict[bytes, tuple[int, int]]:
    table_count = struct.unpack_from(">H", font, 4)[0]
    return {
        tag: (offset, length)
        for tag, _, offset, length in (
            struct.unpack_from(">4sIII", font, 12 + index * 16)
            for index in range(table_count)
        )
    }


def _font_glyphs(font: bytes, codepoints: set[int]) -> dict[int, int]:
    tables = _font_tables(font)
    cmap_offset, _ = tables[b"cmap"]
    cmap_count = struct.unpack_from(">H", font, cmap_offset + 2)[0]
    subtables = []
    for index in range(cmap_count):
        platform, encoding, offset = struct.unpack_from(
            ">HHI", font, cmap_offset + 4 + index * 8
        )
        subtable_offset = cmap_offset + offset
        format_number = struct.unpack_from(">H", font, subtable_offset)[0]
        if format_number in (4, 12):
            subtables.append((platform, encoding, format_number, subtable_offset))

    for _, _, format_number, offset in sorted(
        subtables, key=lambda item: item[2] != 12
    ):
        glyphs: dict[int, int] = {}
        if format_number == 12:
            group_count = struct.unpack_from(">I", font, offset + 12)[0]
            for index in range(group_count):
                start, end, first_glyph = struct.unpack_from(
                    ">III", font, offset + 16 + index * 12
                )
                for codepoint in codepoints:
                    if start <= codepoint <= end:
                        glyphs[codepoint] = first_glyph + codepoint - start
        else:
            segment_count = struct.unpack_from(">H", font, offset + 6)[0] // 2
            end_codes_offset = offset + 14
            start_codes_offset = end_codes_offset + segment_count * 2 + 2
            deltas_offset = start_codes_offset + segment_count * 2
            ranges_offset = deltas_offset + segment_count * 2
            for index in range(segment_count):
                end_code = struct.unpack_from(
                    ">H", font, end_codes_offset + index * 2
                )[0]
                start_code = struct.unpack_from(
                    ">H", font, start_codes_offset + index * 2
                )[0]
                delta = struct.unpack_from(">h", font, deltas_offset + index * 2)[0]
                range_offset = struct.unpack_from(
                    ">H", font, ranges_offset + index * 2
                )[0]
                for codepoint in codepoints:
                    if start_code <= codepoint <= end_code:
                        if range_offset == 0:
                            glyph = (codepoint + delta) & 0xFFFF
                        else:
                            glyph_offset = (
                                ranges_offset
                                + index * 2
                                + range_offset
                                + (codepoint - start_code) * 2
                            )
                            glyph = struct.unpack_from(">H", font, glyph_offset)[0]
                            if glyph:
                                glyph = (glyph + delta) & 0xFFFF
                        glyphs[codepoint] = glyph
        if codepoints <= glyphs.keys():
            return glyphs

    missing = codepoints - glyphs.keys()
    raise ValueError(f"Korean font does not contain required characters: {missing!r}")


def _font_metrics(
    font: bytes, glyphs: dict[int, int]
) -> tuple[dict[int, int], tuple[int, int, int, int], int, int]:
    tables = _font_tables(font)
    head_offset, _ = tables[b"head"]
    hhea_offset, _ = tables[b"hhea"]
    hmtx_offset, _ = tables[b"hmtx"]
    maxp_offset, _ = tables[b"maxp"]
    units_per_em = struct.unpack_from(">H", font, head_offset + 18)[0]
    bbox = struct.unpack_from(">hhhh", font, head_offset + 36)
    ascent, descent = struct.unpack_from(">hh", font, hhea_offset + 4)
    metric_count = struct.unpack_from(">H", font, hhea_offset + 34)[0]
    glyph_count = struct.unpack_from(">H", font, maxp_offset + 4)[0]
    advances = [
        struct.unpack_from(">H", font, hmtx_offset + index * 4)[0]
        for index in range(metric_count)
    ]
    widths = {}
    for codepoint, glyph in glyphs.items():
        if glyph >= glyph_count:
            raise ValueError(f"Invalid glyph index {glyph} for U+{codepoint:04X}.")
        advance = advances[min(glyph, metric_count - 1)]
        widths[codepoint] = round(advance * 1000 / units_per_em)
    scaled_bbox = tuple(round(value * 1000 / units_per_em) for value in bbox)
    return (
        widths,
        scaled_bbox,
        round(ascent * 1000 / units_per_em),
        round(descent * 1000 / units_per_em),
    )


def _load_korean_font(
    texts: list[str],
) -> tuple[bytes, dict[int, int], tuple[int, int, int, int], int, int]:
    font_path = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    if not font_path.is_file():
        raise FileNotFoundError(
            "Korean PDF generation requires NanumGothic "
            "(Debian package: fonts-nanum)."
        )
    font = font_path.read_bytes()
    codepoints = {ord(character) for text in texts for character in text}
    if any(codepoint > 0xFFFF for codepoint in codepoints):
        raise ValueError("PDF report text must use BMP characters.")
    glyphs = _font_glyphs(font, codepoints)
    widths, bbox, ascent, descent = _font_metrics(font, glyphs)
    return font, widths, bbox, ascent, descent


def _pdf_text(x: float, y: float, size: float, value: str) -> str:
    encoded = "".join(f"{ord(character):04X}" for character in value)
    return f"BT /F1 {size:.1f} Tf {x:.2f} {y:.2f} Td <{encoded}> Tj ET"


def _pdf_font_objects(texts: list[str]) -> list[bytes]:
    font, widths, bbox, ascent, descent = _load_korean_font(texts)
    codepoints = sorted(widths)
    maximum_codepoint = max(codepoints, default=0)
    glyphs = _font_glyphs(font, set(codepoints))
    cid_to_gid = bytearray((maximum_codepoint + 1) * 2)
    for codepoint, glyph in glyphs.items():
        struct.pack_into(">H", cid_to_gid, codepoint * 2, glyph)
    width_entries = " ".join(
        f"{codepoint} [{widths[codepoint]}]" for codepoint in codepoints
    )
    mappings = [
        f"<{codepoint:04X}> <{codepoint:04X}>" for codepoint in codepoints
    ]
    cmap_lines = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        "/CMapName /Adobe-Identity-UCS def",
        "/CMapType 2 def",
        "1 begincodespacerange",
        "<0000> <FFFF>",
        "endcodespacerange",
    ]
    for start in range(0, len(mappings), 100):
        chunk = mappings[start : start + 100]
        cmap_lines.append(f"{len(chunk)} beginbfchar")
        cmap_lines.extend(chunk)
        cmap_lines.append("endbfchar")
    cmap_lines.extend(
        [
            "endcmap",
            "CMapName currentdict /CMap defineresource pop",
            "end",
            "end",
        ]
    )
    cmap_data = "\n".join(cmap_lines).encode("ascii")
    compressed_font = compress(font)
    compressed_cid_map = compress(bytes(cid_to_gid))
    compressed_cmap = compress(cmap_data)
    return [
        b"<< /Type /Font /Subtype /Type0 /BaseFont /NanumGothic "
        b"/Encoding /Identity-H /DescendantFonts [8 0 R] /ToUnicode 12 0 R >>",
        (
            "<< /Type /Font /Subtype /CIDFontType2 /BaseFont /NanumGothic "
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
            "/FontDescriptor 9 0 R /DW 1000 /W ["
            f"{width_entries}] /CIDToGIDMap 11 0 R >>"
        ).encode("ascii"),
        (
            "<< /Type /FontDescriptor /FontName /NanumGothic "
            f"/Flags 4 /FontBBox [{bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}] "
            f"/ItalicAngle 0 /Ascent {ascent} /Descent {descent} "
            "/CapHeight 700 /StemV 80 /FontFile2 10 0 R >>"
        ).encode("ascii"),
        (
            f"<< /Length {len(compressed_font)} /Length1 {len(font)} "
            "/Filter /FlateDecode >>\nstream\n"
        ).encode("ascii")
        + compressed_font
        + b"\nendstream",
        (
            f"<< /Length {len(compressed_cid_map)} /Filter /FlateDecode >>\nstream\n"
        ).encode("ascii")
        + compressed_cid_map
        + b"\nendstream",
        (
            f"<< /Length {len(compressed_cmap)} /Filter /FlateDecode >>\nstream\n"
        ).encode("ascii")
        + compressed_cmap
        + b"\nendstream",
    ]


def make_pdf(
    results: list[ExperimentResult], chaining_results: list[ChainingResult]
) -> bytes:
    width, height = 842, 595
    commands = ["1 J 1 j"]
    report_text: list[str] = []
    colors = ((0.09, 0.41, 0.67), (0.82, 0.35, 0.0))

    def add_text(x: float, y: float, size: float, value: str) -> None:
        report_text.append(value)
        commands.append(_pdf_text(x, y, size, value))

    def add_line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = (0.2, 0.2, 0.2),
        dashed: bool = False,
        line_width: float = 0.8,
    ) -> None:
        dash = "[4 3] 0 d" if dashed else "[] 0 d"
        commands.append(
            f"q {color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG "
            f"{line_width:.1f} w {dash} {x1:.2f} {y1:.2f} m "
            f"{x2:.2f} {y2:.2f} l S Q"
        )

    add_text(55, 561, 19, "해시 충돌 처리 방식 비교 실험")
    add_text(
        55,
        542,
        9,
        f"URL 단축기 · 탐색 비용 측정과 이론값 비교 · 용량 {CAPACITY}",
    )
    panel_specs = (
        (
            55,
            "체이닝",
            "chaining_successful_avg_probes",
            "chaining_successful_theory",
            "chaining_unsuccessful_avg_probes",
            "chaining_unsuccessful_theory",
        ),
        (
            435,
            "선형 탐지",
            "linear_successful_avg_probes",
            "linear_successful_theory",
            "linear_unsuccessful_avg_probes",
            "linear_unsuccessful_theory",
        ),
    )
    for (
        panel_x,
        title,
        success_measured,
        success_theory,
        failure_measured,
        failure_theory,
    ) in panel_specs:
        plot_x, plot_y = panel_x + 46, 270
        plot_width, plot_height = 320, 218
        maximum = max(
            getattr(result, field)
            for result in results
            for field in (
                success_measured,
                success_theory,
                failure_measured,
                failure_theory,
            )
        )
        y_max = math.ceil(maximum / 5) * 5
        if y_max == 0:
            y_max = 1

        def x_position(alpha: float) -> float:
            return plot_x + (alpha - 0.1) / 0.8 * plot_width

        def y_position(value: float) -> float:
            return plot_y + value / y_max * plot_height

        add_text(panel_x + 105, 511, 12, title)
        legend_entries = (
            ("성공 측정", colors[0], False),
            ("성공 이론", colors[0], True),
            ("실패 측정", colors[1], False),
            ("실패 이론", colors[1], True),
        )
        for index, (label, color, dashed) in enumerate(legend_entries):
            legend_x = panel_x + 12 + (index % 2) * 185
            legend_y = 493 - (index // 2) * 13
            add_line(legend_x, legend_y, legend_x + 18, legend_y, color, dashed, 1.4)
            add_text(legend_x + 22, legend_y - 3, 7.5, label)

        for tick in range(5):
            value = y_max * tick / 4
            y = y_position(value)
            add_line(plot_x, y, plot_x + plot_width, y, (0.85, 0.85, 0.85))
            add_text(plot_x - 27, y - 2, 7, f"{value:.0f}")
        for tick in (0.1, 0.3, 0.5, 0.7, 0.9):
            x = x_position(tick)
            add_line(x, plot_y, x, plot_y + plot_height, (0.92, 0.92, 0.92))
            add_text(x - 7, plot_y - 14, 7, f"{tick:.1f}")
        add_line(plot_x, plot_y, plot_x + plot_width, plot_y, line_width=1)
        add_line(plot_x, plot_y, plot_x, plot_y + plot_height, line_width=1)
        add_text(plot_x + 126, plot_y - 29, 8, "적재율 α")

        fields = (success_measured, success_theory, failure_measured, failure_theory)
        for series_index, field in enumerate(fields):
            color = colors[series_index // 2]
            dashed = series_index % 2 == 1
            previous = None
            for result in results:
                point = (
                    x_position(result.actual_alpha),
                    y_position(getattr(result, field)),
                )
                if previous is not None:
                    add_line(
                        previous[0],
                        previous[1],
                        point[0],
                        point[1],
                        color,
                        dashed,
                        1.5,
                    )
                previous = point

    at_nine_tenths = results[-1]
    add_text(
        55,
        229,
        8.5,
        "구현: 공통 Horner 해시를 사용하며, 체이닝은 버킷 리스트에 충돌 키를 저장한다. 선형 탐지는 다음 슬롯을 조사하고 끝에서 순환한다.",
    )
    add_text(
        55,
        213,
        9,
        f"조건: 용량 {CAPACITY}, 시드 {RANDOM_SEED}, 동일 URL 키, 적재율 α=0.1~0.9 (0.1 간격).",
    )
    add_text(
        55,
        197,
        9,
        f"성공은 저장 키 전수, 실패는 미등록 URL {FAILURE_QUERY_COUNT}개 탐색 평균; 실선은 측정, 점선은 이론.",
    )
    add_text(55, 177, 9, "체이닝 이론: 성공 1+α/2, 실패 α.")
    add_text(
        55,
        162,
        9,
        "선형 탐지 이론: 성공 ½(1+1/(1-α)), 실패 ½(1+1/(1-α)²).",
    )
    add_text(
        55,
        137,
        9.5,
        (
            f"α=0.9 성공 탐색: 체이닝 {at_nine_tenths.chaining_successful_avg_probes:.3f}회, "
            f"선형 탐지 {at_nine_tenths.linear_successful_avg_probes:.3f}회."
        ),
    )
    add_text(
        55,
        121,
        9.5,
        (
            f"실패 탐색: 체이닝 {at_nine_tenths.chaining_unsuccessful_avg_probes:.3f}회, "
            f"선형 탐지 {at_nine_tenths.linear_unsuccessful_avg_probes:.3f}회."
        ),
    )
    add_text(
        55,
        96,
        9,
        "상세 해석과 체이닝의 고적재율 실험은 다음 쪽에 이어진다.",
    )
    add_text(
        55,
        77,
        8,
        "원자료: results.csv · 그래프: results.svg",
    )

    first_page_stream = ("\n".join(commands) + "\n").encode("ascii")

    second_commands = ["1 J 1 j"]

    def add_second_text(x: float, y: float, size: float, value: str) -> None:
        report_text.append(value)
        second_commands.append(_pdf_text(x, y, size, value))

    def add_second_line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = (0.2, 0.2, 0.2),
        dashed: bool = False,
        line_width: float = 0.8,
    ) -> None:
        dash = "[4 3] 0 d" if dashed else "[] 0 d"
        second_commands.append(
            f"q {color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG "
            f"{line_width:.1f} w {dash} {x1:.2f} {y1:.2f} m "
            f"{x2:.2f} {y2:.2f} l S Q"
        )

    add_second_text(55, 561, 19, "고적재율 체이닝과 진행 과정 분석")
    add_second_text(
        55,
        542,
        9,
        f"기존 Step 6 실험 범위: α=0.25~4.0 · 테이블 용량 {CAPACITY}",
    )
    plot_x, plot_y = 100, 338
    plot_width, plot_height = 660, 150
    y_max = math.ceil(
        max(
            getattr(result, field)
            for result in chaining_results
            for field in (
                "successful_avg_probes",
                "successful_theory",
                "unsuccessful_avg_probes",
                "unsuccessful_theory",
            )
        )
    )

    def chaining_x(alpha: float) -> float:
        return plot_x + alpha / 4 * plot_width

    def chaining_y(value: float) -> float:
        return plot_y + value / y_max * plot_height

    high_load_series = (
        ("성공 측정", "successful_avg_probes", colors[0], False),
        ("성공 이론", "successful_theory", colors[0], True),
        ("실패 측정", "unsuccessful_avg_probes", colors[1], False),
        ("실패 이론", "unsuccessful_theory", colors[1], True),
    )
    for index, (label, _, color, dashed) in enumerate(high_load_series):
        legend_x = 95 + (index % 2) * 260
        legend_y = 513 - (index // 2) * 16
        add_second_line(
            legend_x, legend_y, legend_x + 20, legend_y, color, dashed, 1.4
        )
        add_second_text(legend_x + 25, legend_y - 3, 8, label)
    for tick in range(y_max + 1):
        y = chaining_y(float(tick))
        add_second_line(
            plot_x, y, plot_x + plot_width, y, (0.85, 0.85, 0.85)
        )
        add_second_text(plot_x - 28, y - 2, 7, str(tick))
    for tick in range(17):
        alpha = tick / 4
        x = chaining_x(alpha)
        add_second_line(
            x, plot_y, x, plot_y + plot_height, (0.92, 0.92, 0.92)
        )
        if tick % 2 == 0:
            add_second_text(x - 7, plot_y - 14, 7, f"{alpha:g}")
    add_second_line(
        plot_x, plot_y, plot_x + plot_width, plot_y, line_width=1
    )
    add_second_line(
        plot_x, plot_y, plot_x, plot_y + plot_height, line_width=1
    )
    add_second_text(plot_x + 302, plot_y - 29, 8, "적재율 α")
    for _, field, color, dashed in high_load_series:
        previous = None
        for result in chaining_results:
            point = (
                chaining_x(result.actual_alpha),
                chaining_y(getattr(result, field)),
            )
            if previous is not None:
                add_second_line(
                    previous[0],
                    previous[1],
                    point[0],
                    point[1],
                    color,
                    dashed,
                    1.5,
                )
            previous = point

    at_four = chaining_results[-1]
    add_second_text(
        55,
        286,
        9,
        f"각 적재율에서 저장 키 전수와 미등록 URL {FAILURE_QUERY_COUNT}개를 평균했다.",
    )
    add_second_text(
        55,
        271,
        9,
        "α=4.0 체이닝: 성공 "
        f"{at_four.successful_avg_probes:.6f}회(이론 {at_four.successful_theory:.3f}), "
        f"실패 {at_four.unsuccessful_avg_probes:.6f}회(이론 {at_four.unsuccessful_theory:.3f}).",
    )
    add_second_text(
        55,
        254,
        9,
        "체이닝은 적재율이 1을 넘어도 삽입할 수 있으며, 비용은 평균 버킷 체인 길이에 따라 증가한다.",
    )
    add_second_text(
        55,
        239,
        9,
        "반면 선형 탐지는 빈 슬롯이 줄수록 충돌 뒤 연속 구간(primary clustering)이 길어진다.",
    )
    add_second_text(
        55,
        220,
        9,
        "특히 실패 탐색은 빈 슬롯을 만날 때까지 군집을 훑어 α가 1에 가까워지면 비용이 급격히 커진다.",
    )
    add_second_text(
        55,
        205,
        9,
        "체이닝은 이런 연속 군집 없이 평균 버킷 길이에 따라 완만하게 증가한다.",
    )
    add_second_text(55, 187, 10, "진행 중 바로잡은 점")
    add_second_text(
        55,
        171,
        8.5,
        "명세 대조에서 dict 사용, 해시값 기반 코드 생성, 테스트 작성 순서의 불일치를 지적해 재점검했다.",
    )
    add_second_text(
        55,
        156,
        8.5,
        "이슈 #3의 계획 단계가 Step 2와 Step 4 사이에 오도록 순서를 바로잡았다.",
    )
    add_second_text(
        55,
        141,
        8.5,
        "이슈 체크리스트와 파일·CSV/SVG를 대조해 src/shortener.py 누락 및 Step 6 결과 덮어쓰기를 발견하고 복구했다.",
    )
    add_second_text(
        55,
        126,
        8.5,
        "원격 브랜치 기록 비교로 제출 파일은 develop에 있고 기본 main에는 없어 보였던 원인도 확인했다.",
    )
    add_second_text(
        55,
        111,
        8,
        "발견 근거: 명세·이슈 체크박스, 생성 파일과 데이터, 커밋 브랜치를 서로 대조한 점검.",
    )
    add_second_text(55, 89, 10, "느낀 점")
    add_second_text(
        55,
        73,
        8.5,
        "에이전틱 코딩은 간결한 지시로 구현·검증을 진행하고 파일·이슈 기록으로 오류를 빠르게 추적하게 해 생산적이었다.",
    )
    add_second_text(
        55,
        58,
        8.5,
        "반면 낯선 오류를 판단하기 어렵고, AI의 요청을 충분히 이해하지 못한 채 수락하거나 설정을 빠뜨려 작업이 멈추기도 했다.",
    )
    add_second_text(
        55,
        43,
        8.5,
        "AI를 효율적으로 활용하려면 도구의 발전과 함께 해당 분야의 기초 지식과 산출물 검토 역량이 필요함을 배웠다.",
    )
    second_page_stream = ("\n".join(second_commands) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            "/Resources << /Font << /F1 7 0 R >> >> /Contents 4 0 R >>"
        ).encode("ascii"),
        f"<< /Length {len(first_page_stream)} >>\nstream\n".encode("ascii")
        + first_page_stream
        + b"endstream",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            "/Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>"
        ).encode("ascii"),
        f"<< /Length {len(second_page_stream)} >>\nstream\n".encode("ascii")
        + second_page_stream
        + b"endstream",
    ]
    objects.extend(_pdf_font_objects(report_text))
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, object_data in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(object_data)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def main() -> None:
    output_directory = Path(__file__).resolve().parent
    results = measure()
    chaining_results = measure_chaining()
    write_csv(results, output_directory / "results.csv")
    (output_directory / "results.svg").write_text(make_svg(results), encoding="utf-8")
    write_chaining_csv(chaining_results, output_directory / "chaining_results.csv")
    (output_directory / "chaining_results.svg").write_text(
        make_chaining_svg(chaining_results), encoding="utf-8"
    )
    (output_directory / "report.pdf").write_bytes(
        make_pdf(results, chaining_results)
    )
    print(
        f"Wrote {len(results)} comparison and {len(chaining_results)} chaining "
        f"measurements to CSV/SVG outputs and {output_directory / 'report.pdf'}"
    )


if __name__ == "__main__":
    main()
