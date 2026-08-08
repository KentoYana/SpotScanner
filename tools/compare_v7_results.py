#!/usr/bin/env python3
"""Compare SpotScanner 8 output with archived SpotScanner 7 result CSVs."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_RELATIVE_PATH = Path("04_quantitative_spot_test/dataset")
CURRENT_FIELDS = ["Time", "Image", "Threshold", "row", "column", "Colony"]
MODE_DIMENSIONS = {"pipette": (4, 6), "replicator": (8, 12)}

# Running ``python tools/compare_v7_results.py`` puts ``tools`` rather than the
# checkout root on sys.path.  Add the root explicitly so that both the report
# metadata and the subprocesses exercise the current source tree, even when the
# selected pyenv interpreter does not have SpotScanner installed.
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(frozen=True)
class Case:
    index: int
    reference_csv: Path
    image: Path
    threshold: int
    reference_rows: tuple[dict[str, str], ...]

    @property
    def image_stem(self) -> str:
        return self.reference_csv.name.removesuffix("_results.csv")


@dataclass(frozen=True)
class CaseResult:
    case: Case
    differences: tuple[dict[str, Any], ...]
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Re-run archived plate images with the current SpotScanner source "
            "and compare the generated values with SpotScanner 7 CSVs."
        )
    )
    parser.add_argument(
        "resource_repository",
        type=Path,
        help=(
            "Path to a Resource_Article_DDT_hH3-K4R_01 checkout or another "
            "directory containing archived *_results.csv files."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_DIMENSIONS),
        default="pipette",
        help="Analysis grid used by the archived results (default: pipette).",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=min(4, os.cpu_count() or 1),
        help="Number of image analyses to run concurrently (default: up to 4).",
    )
    parser.add_argument(
        "--tolerance",
        type=Decimal,
        default=Decimal("0"),
        help="Allowed absolute Colony difference after two-decimal output (default: 0).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Analyze only the first N cases, for a quick local check.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Write a machine-readable JSON report to this path.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Keep generated CSV and diagnostic images in this directory.",
    )
    parser.add_argument(
        "--skip-missing-images",
        action="store_true",
        help=(
            "Report and skip result CSVs whose source image cannot be found "
            "by basename instead of rejecting the dataset."
        ),
    )
    parser.add_argument(
        "--skip-incompatible-results",
        action="store_true",
        help=(
            "Report and skip result CSVs with an incompatible schema or grid "
            "instead of rejecting the dataset."
        ),
    )
    parser.add_argument(
        "--image-alias",
        action="append",
        default=[],
        metavar="RESULT_STEM=IMAGE_STEM",
        help=(
            "Map a result basename to a renamed source-image basename. "
            "May be supplied more than once."
        ),
    )
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.tolerance < 0:
        parser.error("--tolerance cannot be negative")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    aliases = {}
    for value in args.image_alias:
        result_stem, separator, image_stem = value.partition("=")
        if not separator or not result_stem or not image_stem:
            parser.error("--image-alias must use RESULT_STEM=IMAGE_STEM")
        if result_stem in aliases:
            parser.error(f"duplicate --image-alias for {result_stem}")
        aliases[result_stem] = image_stem
    args.image_aliases = aliases
    return args


def read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != CURRENT_FIELDS:
            raise ValueError(
                f"unexpected columns in {path}: {reader.fieldnames!r}; "
                f"expected {CURRENT_FIELDS!r}"
            )
        return tuple(dict(row) for row in reader)


def find_image(reference_csv: Path, image_stem: str) -> Path:
    image_directory = reference_csv.parent.parent
    matches = [
        path
        for path in image_directory.iterdir()
        if path.is_file()
        and path.stem == image_stem
        and path.suffix.lower() in {".jpg", ".jpeg"}
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one source image for {reference_csv}, found {len(matches)}"
        )
    return matches[0]


def discover_cases(
    resource_repository: Path,
    mode: str,
    skip_missing_images: bool,
    skip_incompatible_results: bool,
    image_aliases: dict[str, str],
) -> tuple[list[Case], list[dict[str, str]], Path]:
    packaged_dataset_root = resource_repository.resolve() / DATASET_RELATIVE_PATH
    dataset_root = (
        packaged_dataset_root
        if packaged_dataset_root.is_dir()
        else resource_repository.resolve()
    )
    if not dataset_root.is_dir():
        raise ValueError(f"dataset directory not found: {dataset_root}")

    cases = []
    skipped = []
    expected_rows = MODE_DIMENSIONS[mode][0] * MODE_DIMENSIONS[mode][1]
    for index, reference_csv in enumerate(
        sorted(dataset_root.rglob("*_results.csv")), start=1
    ):
        try:
            rows = read_csv_rows(reference_csv)
            if len(rows) != expected_rows:
                raise ValueError(
                    f"expected {expected_rows} measurement rows in {reference_csv}"
                )
            thresholds = {row["Threshold"] for row in rows}
            if len(thresholds) != 1:
                raise ValueError(f"multiple thresholds in {reference_csv}: {thresholds}")
            image_stem = reference_csv.name.removesuffix("_results.csv")
            if {row["Image"] for row in rows} != {image_stem}:
                raise ValueError(
                    f"Image column does not match {image_stem}: {reference_csv}"
                )
        except (TypeError, ValueError) as error:
            if not skip_incompatible_results:
                raise
            skipped.append({"reference_csv": str(reference_csv), "reason": str(error)})
            continue
        try:
            image = find_image(
                reference_csv,
                image_aliases.get(image_stem, image_stem),
            )
        except ValueError as error:
            if not skip_missing_images:
                raise
            skipped.append({"reference_csv": str(reference_csv), "reason": str(error)})
            continue
        cases.append(
            Case(
                index=index,
                reference_csv=reference_csv,
                image=image,
                threshold=int(next(iter(thresholds))),
                reference_rows=rows,
            )
        )
    if not cases:
        raise ValueError(f"no SpotScanner result CSV files found below {dataset_root}")
    return cases, skipped, dataset_root


def rows_by_position(rows: tuple[dict[str, str], ...]) -> dict[tuple[int, int], dict[str, str]]:
    indexed = {(int(row["row"]), int(row["column"])): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("duplicate row/column coordinates")
    return indexed


def compare_rows(
    case: Case,
    generated_rows: tuple[dict[str, str], ...],
    tolerance: Decimal,
) -> tuple[dict[str, Any], ...]:
    reference = rows_by_position(case.reference_rows)
    generated = rows_by_position(generated_rows)
    if set(reference) != set(generated):
        missing = sorted(set(reference) - set(generated))
        unexpected = sorted(set(generated) - set(reference))
        raise ValueError(f"coordinate mismatch; missing={missing}, unexpected={unexpected}")

    differences = []
    for position in sorted(reference):
        expected = reference[position]
        actual = generated[position]
        for field in ("Image", "Threshold", "row", "column"):
            if expected[field] != actual[field]:
                raise ValueError(
                    f"metadata mismatch at {position} for {field}: "
                    f"{expected[field]!r} != {actual[field]!r}"
                )
        if expected["Colony"].strip().upper() == "NA":
            continue
        try:
            expected_colony = Decimal(expected["Colony"])
            actual_colony = Decimal(actual["Colony"])
        except InvalidOperation as error:
            raise ValueError(
                f"non-numeric Colony value at {position}: "
                f"{expected['Colony']!r} != {actual['Colony']!r}"
            ) from error
        absolute_difference = abs(actual_colony - expected_colony)
        if absolute_difference > tolerance:
            differences.append(
                {
                    "row": position[0],
                    "column": position[1],
                    "expected": float(expected_colony),
                    "actual": float(actual_colony),
                    "absolute_difference": float(absolute_difference),
                }
            )
    return tuple(differences)


def run_case(
    case: Case,
    work_root: Path,
    tolerance: Decimal,
    mode: str,
) -> CaseResult:
    case_directory = work_root / f"{case.index:04d}"
    case_directory.mkdir(parents=True, exist_ok=False)
    linked_image = case_directory / f"{case.image_stem}{case.image.suffix}"
    linked_image.symlink_to(case.image)

    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    if existing_pythonpath:
        environment["PYTHONPATH"] += os.pathsep + existing_pythonpath

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "spotscanner",
            "--analyze",
            mode,
            "--single",
            linked_image.name,
            "--threshold",
            str(case.threshold),
        ],
        cwd=case_directory,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return CaseResult(
            case=case,
            differences=(),
            error=(
                f"SpotScanner exited {completed.returncode}; "
                f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
            ),
        )

    generated_csv = case_directory / f"{case.image_stem}_results.csv"
    if not generated_csv.is_file():
        return CaseResult(
            case=case,
            differences=(),
            error=f"generated CSV not found: {generated_csv}; stdout={completed.stdout!r}",
        )
    try:
        generated_rows = read_csv_rows(generated_csv)
        differences = compare_rows(case, generated_rows, tolerance)
    except (OSError, TypeError, ValueError) as error:
        return CaseResult(case=case, differences=(), error=str(error))
    return CaseResult(case=case, differences=differences)


def git_commit(repository: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return None


def git_dirty(repository: Path) -> bool | None:
    completed = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return bool(completed.stdout.strip())
    return None


def make_report(
    resource_repository: Path,
    cases: list[Case],
    results: list[CaseResult],
    tolerance: Decimal,
    mode: str,
    dataset_root: Path,
    skipped: list[dict[str, str]],
    image_aliases: dict[str, str],
) -> dict[str, Any]:
    differences = [
        {
            "reference_csv": str(result.case.reference_csv),
            "image": str(result.case.image),
            **difference,
        }
        for result in results
        for difference in result.differences
    ]
    errors = [
        {
            "reference_csv": str(result.case.reference_csv),
            "image": str(result.case.image),
            "error": result.error,
        }
        for result in results
        if result.error is not None
    ]
    total_cells = sum(len(case.reference_rows) for case in cases)
    reference_na_cells = sum(
        row["Colony"].strip().upper() == "NA"
        for case in cases
        for row in case.reference_rows
    )
    return {
        "resource_repository": str(resource_repository.resolve()),
        "dataset_root": str(dataset_root),
        "resource_commit": git_commit(resource_repository.resolve()),
        "resource_dirty": git_dirty(resource_repository.resolve()),
        "spotscanner_commit": git_commit(PROJECT_ROOT),
        "spotscanner_dirty": git_dirty(PROJECT_ROOT),
        "spotscanner_version": __import__("spotscanner").__version__,
        "python_version": sys.version.split()[0],
        "numpy_version": __import__("numpy").__version__,
        "opencv_version": __import__("cv2").__version__,
        "mode": mode,
        "image_aliases": image_aliases,
        "tolerance": float(tolerance),
        "cases": len(cases),
        "cells": total_cells,
        "compared_cells": total_cells - reference_na_cells,
        "reference_na_cells": reference_na_cells,
        "skipped": skipped,
        "threshold_counts": dict(sorted(Counter(case.threshold for case in cases).items())),
        "cases_with_differences": len(
            {result.case.reference_csv for result in results if result.differences}
        ),
        "different_cells": len(differences),
        "max_absolute_difference": max(
            (difference["absolute_difference"] for difference in differences),
            default=0.0,
        ),
        "errors": errors,
        "differences": differences,
    }


def main() -> int:
    args = parse_args()
    resource_repository = args.resource_repository.resolve()
    try:
        cases, skipped, dataset_root = discover_cases(
            resource_repository,
            args.mode,
            args.skip_missing_images,
            args.skip_incompatible_results,
            args.image_aliases,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if args.limit is not None:
        cases = cases[: args.limit]
    print(
        f"Discovered {len(cases)} image/CSV pairs; "
        f"mode={args.mode}; "
        f"thresholds={dict(sorted(Counter(case.threshold for case in cases).items()))}; "
        f"skipped={len(skipped)}",
        flush=True,
    )

    temporary_directory = None
    if args.work_dir is None:
        temporary_directory = tempfile.mkdtemp(prefix="spotscanner-v7-regression-")
        work_root = Path(temporary_directory)
    else:
        work_root = args.work_dir.resolve()
        work_root.mkdir(parents=True, exist_ok=False)

    results = []
    try:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            future_to_case = {
                executor.submit(
                    run_case,
                    case,
                    work_root,
                    args.tolerance,
                    args.mode,
                ): case
                for case in cases
            }
            for completed_count, future in enumerate(as_completed(future_to_case), start=1):
                result = future.result()
                results.append(result)
                if completed_count % 10 == 0 or completed_count == len(cases):
                    print(f"Completed {completed_count}/{len(cases)}", flush=True)

        results.sort(key=lambda result: result.case.index)
        report = make_report(
            resource_repository,
            cases,
            results,
            args.tolerance,
            args.mode,
            dataset_root,
            skipped,
            args.image_aliases,
        )
        if args.report is not None:
            report_path = args.report.resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"Report: {report_path}")

        print(
            "Summary: "
            f"cases={report['cases']}, compared_cells={report['compared_cells']}, "
            f"reference_na_cells={report['reference_na_cells']}, "
            f"skipped={len(report['skipped'])}, "
            f"cases_with_differences={report['cases_with_differences']}, "
            f"different_cells={report['different_cells']}, "
            f"max_absolute_difference={report['max_absolute_difference']}, "
            f"errors={len(report['errors'])}",
            flush=True,
        )
        if report["errors"]:
            for error in report["errors"][:10]:
                print(f"Error: {error}", file=sys.stderr)
        return 0 if not report["errors"] and not report["differences"] else 1
    finally:
        if temporary_directory is not None:
            shutil.rmtree(temporary_directory)


if __name__ == "__main__":
    raise SystemExit(main())
