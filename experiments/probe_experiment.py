"""Compare separate chaining and linear probing across load factors."""

import csv
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

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
            "Separate chaining",
            "chaining_successful_avg_probes",
            "chaining_successful_theory",
            "chaining_unsuccessful_avg_probes",
            "chaining_unsuccessful_theory",
        ),
        (
            "Linear probing",
            "linear_successful_avg_probes",
            "linear_successful_theory",
            "linear_unsuccessful_avg_probes",
            "linear_unsuccessful_theory",
        ),
    )
    colors = ("#1769aa", "#d05a00")
    series_labels = (
        "successful",
        "successful theory",
        "unsuccessful",
        "unsuccessful theory",
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Separate chaining and linear probing probe counts</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#222">',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-size="21">Hash table probe costs by load factor</text>',
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
                f'<text x="{plot_left + plot_width / 2}" y="{panel_bottom - 10}" text-anchor="middle">Load factor alpha</text>',
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
            f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle">Same keys, table capacity {CAPACITY}; dashed lines are theoretical estimates</text>',
            "</g>",
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def _pdf_text(x: float, y: float, size: float, value: str) -> str:
    safe_value = value.encode("ascii", "replace").decode("ascii")
    safe_value = safe_value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size:.1f} Tf {x:.2f} {y:.2f} Td ({safe_value}) Tj ET"


def make_pdf(
    results: list[ExperimentResult], chaining_results: list[ChainingResult]
) -> bytes:
    width, height = 842, 595
    commands = ["1 J 1 j"]
    colors = ((0.09, 0.41, 0.67), (0.82, 0.35, 0.0))

    def add_text(x: float, y: float, size: float, value: str) -> None:
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

    add_text(55, 561, 19, "Linear probing vs. separate chaining")
    add_text(
        55,
        542,
        9,
        f"Measured mean probes and theory, load factor 0.1-0.9, table capacity {CAPACITY}.",
    )
    panel_specs = (
        (
            55,
            "Separate chaining",
            "chaining_successful_avg_probes",
            "chaining_successful_theory",
            "chaining_unsuccessful_avg_probes",
            "chaining_unsuccessful_theory",
        ),
        (
            435,
            "Linear probing",
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
            ("success measured", colors[0], False),
            ("success theory", colors[0], True),
            ("failure measured", colors[1], False),
            ("failure theory", colors[1], True),
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
        add_text(plot_x + 116, plot_y - 29, 8, "Load factor alpha")

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
    add_text(55, 213, 9.5, "Method: both tables use the same deterministic URL keys and capacity.")
    add_text(55, 197, 9.5, "Each point averages every stored key (success) and 4,093 absent keys (failure).")
    add_text(55, 177, 9, "Chaining estimates: success = 1 + alpha/2; failure = alpha.")
    add_text(
        55,
        162,
        9,
        "Linear probing estimates: success = 0.5*(1 + 1/(1-alpha)); failure = 0.5*(1 + 1/(1-alpha)^2).",
    )
    add_text(
        55,
        137,
        9.5,
        (
            "At alpha 0.9, measured successful probes: chaining "
            f"{at_nine_tenths.chaining_successful_avg_probes:.2f}, linear "
            f"{at_nine_tenths.linear_successful_avg_probes:.2f}."
        ),
    )
    add_text(
        55,
        121,
        9.5,
        (
            "Measured unsuccessful probes: chaining "
            f"{at_nine_tenths.chaining_unsuccessful_avg_probes:.2f}, linear "
            f"{at_nine_tenths.linear_unsuccessful_avg_probes:.2f}."
        ),
    )
    add_text(
        55,
        96,
        9,
        "Linear probing shows primary clustering, especially for misses; theoretical curves are approximations.",
    )
    add_text(
        55,
        77,
        8,
        f"Reproducible experiment seed: {RANDOM_SEED}. Data: results.csv; vector chart: results.svg.",
    )

    first_page_stream = ("\n".join(commands) + "\n").encode("ascii")

    second_commands = ["1 J 1 j"]

    def add_second_text(x: float, y: float, size: float, value: str) -> None:
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

    add_second_text(55, 561, 19, "Separate chaining at high load factors")
    add_second_text(
        55,
        542,
        9,
        f"Original Step 6 range, alpha 0.25-4.0, capacity {CAPACITY}.",
    )
    plot_x, plot_y = 100, 278
    plot_width, plot_height = 660, 220
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
        ("success measured", "successful_avg_probes", colors[0], False),
        ("success theory", "successful_theory", colors[0], True),
        ("failure measured", "unsuccessful_avg_probes", colors[1], False),
        ("failure theory", "unsuccessful_theory", colors[1], True),
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
    add_second_text(plot_x + 282, plot_y - 29, 8, "Load factor alpha")
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
        230,
        9.5,
        "Each load point averages all stored keys and 4,093 absent keys.",
    )
    add_second_text(
        55,
        212,
        9,
        "Separate chaining estimates: success = 1 + alpha/2; failure = alpha.",
    )
    add_second_text(
        55,
        193,
        9.5,
        (
            f"At alpha 4.0, measured success = {at_four.successful_avg_probes:.3f} "
            f"(theory {at_four.successful_theory:.3f});"
        ),
    )
    add_second_text(
        55,
        177,
        9.5,
        (
            f"measured failure = {at_four.unsuccessful_avg_probes:.3f} "
            f"(theory {at_four.unsuccessful_theory:.3f})."
        ),
    )
    add_second_text(
        55,
        151,
        9,
        "The small differences reflect deterministic hash distribution and finite samples.",
    )
    add_second_text(
        55,
        130,
        8,
        f"Seed {RANDOM_SEED}; full data: chaining_results.csv; graph: chaining_results.svg.",
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
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
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
