"""Measure separate-chaining probe counts across a range of load factors."""

import csv
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(ROOT_DIRECTORY))

from src.hash_table import HashTable

CAPACITY = 4093
FIRST_LOAD_FACTOR_STEP = 1
LAST_LOAD_FACTOR_STEP = 16
FAILURE_QUERY_COUNT = CAPACITY
RANDOM_SEED = 20261120

CSV_FIELDS = (
    "target_alpha",
    "actual_alpha",
    "item_count",
    "successful_avg_probes",
    "successful_theory",
    "unsuccessful_avg_probes",
    "unsuccessful_theory",
)


@dataclass(frozen=True)
class ExperimentResult:
    target_alpha: float
    actual_alpha: float
    item_count: int
    successful_avg_probes: float
    successful_theory: float
    unsuccessful_avg_probes: float
    unsuccessful_theory: float


def random_urls(
    generator: random.Random, namespace: str, count: int
) -> list[str]:
    return [
        f"https://{namespace}.example/{generator.getrandbits(128):032x}-{index}"
        for index in range(count)
    ]


def measure() -> list[ExperimentResult]:
    generator = random.Random(RANDOM_SEED)
    maximum_item_count = CAPACITY * LAST_LOAD_FACTOR_STEP // 4
    keys = random_urls(generator, "stored", maximum_item_count)
    missing_keys = random_urls(generator, "missing", FAILURE_QUERY_COUNT)
    results = []

    for step in range(FIRST_LOAD_FACTOR_STEP, LAST_LOAD_FACTOR_STEP + 1):
        target_alpha = step / 4
        item_count = round(CAPACITY * target_alpha)
        table: HashTable[str] = HashTable(capacity=CAPACITY, max_load=None)
        for key in keys[:item_count]:
            table.put(key, key)

        actual_alpha = len(table) / table.capacity
        successful_average = sum(table.probe_count(key) for key in keys[:item_count])
        successful_average /= item_count
        unsuccessful_average = sum(
            table.probe_count(key) for key in missing_keys
        ) / len(missing_keys)

        results.append(
            ExperimentResult(
                target_alpha=target_alpha,
                actual_alpha=actual_alpha,
                item_count=item_count,
                successful_avg_probes=successful_average,
                successful_theory=1 + actual_alpha / 2,
                unsuccessful_avg_probes=unsuccessful_average,
                unsuccessful_theory=actual_alpha,
            )
        )

    return results


def write_csv(results: list[ExperimentResult], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "target_alpha": f"{result.target_alpha:.2f}",
                    "actual_alpha": f"{result.actual_alpha:.6f}",
                    "item_count": result.item_count,
                    "successful_avg_probes": f"{result.successful_avg_probes:.6f}",
                    "successful_theory": f"{result.successful_theory:.6f}",
                    "unsuccessful_avg_probes": f"{result.unsuccessful_avg_probes:.6f}",
                    "unsuccessful_theory": f"{result.unsuccessful_theory:.6f}",
                }
            )


def make_svg(results: list[ExperimentResult]) -> str:
    width, height = 960, 600
    left, right, top, bottom = 82, 30, 42, 72
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_value = max(
        value
        for result in results
        for value in (
            result.successful_avg_probes,
            result.successful_theory,
            result.unsuccessful_avg_probes,
            result.unsuccessful_theory,
        )
    )
    y_max = math.ceil(max_value * 1.1 * 2) / 2

    def x_position(alpha: float) -> float:
        return left + alpha / 4 * plot_width

    def y_position(value: float) -> float:
        return top + (y_max - value) / y_max * plot_height

    series = (
        ("성공 탐색 측정", "successful_avg_probes", "#1769aa", ""),
        ("성공 탐색 이론", "successful_theory", "#1769aa", "8 5"),
        ("실패 탐색 측정", "unsuccessful_avg_probes", "#d05a00", ""),
        ("실패 탐색 이론", "unsuccessful_theory", "#d05a00", "8 5"),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>적재율에 따른 평균 탐색 노드 수</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#222">',
        f'<text x="{width / 2}" y="24" text-anchor="middle" font-size="18">체이닝 해시 테이블: 측정값과 이론값</text>',
    ]

    tick_count = math.floor(y_max)
    for tick in range(tick_count + 1):
        y = y_position(float(tick))
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#ddd"/>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end">{tick}</text>'
        )
    for tick in range(5):
        x = x_position(float(tick))
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#eee"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 24}" text-anchor="middle">{tick}</text>'
        )

    parts.extend(
        [
            f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#333"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#333"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 20}" text-anchor="middle">적재율 α</text>',
            f'<text x="20" y="{top + plot_height / 2}" text-anchor="middle" transform="rotate(-90 20 {top + plot_height / 2})">평균 비교 노드 수</text>',
        ]
    )

    for index, (label, attribute, color, dash) in enumerate(series):
        points = " ".join(
            f"{x_position(result.actual_alpha):.2f},{y_position(getattr(result, attribute)):.2f}"
            for result in results
        )
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        for result in results:
            value = getattr(result, attribute)
            parts.append(
                f'<circle cx="{x_position(result.actual_alpha):.2f}" cy="{y_position(value):.2f}" r="2.5" fill="{color}"/>'
            )

        legend_y = top + 18 + index * 22
        parts.append(
            f'<line x1="{left + plot_width - 190}" y1="{legend_y}" x2="{left + plot_width - 165}" y2="{legend_y}" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        parts.append(
            f'<text x="{left + plot_width - 158}" y="{legend_y + 4}">{label}</text>'
        )

    parts.extend(["</g>", "</svg>"])
    return "\n".join(parts) + "\n"


def main() -> None:
    output_directory = Path(__file__).resolve().parent
    results = measure()
    write_csv(results, output_directory / "results.csv")
    (output_directory / "results.svg").write_text(
        make_svg(results), encoding="utf-8"
    )
    print(
        f"Wrote {len(results)} load-factor measurements to "
        f"{output_directory / 'results.csv'} and results.svg"
    )


if __name__ == "__main__":
    main()
