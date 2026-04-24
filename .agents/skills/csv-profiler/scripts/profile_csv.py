#!/usr/bin/env python3
"""
profile_csv.py — deterministic CSV data quality profiler.

Usage:
    python profile_csv.py <path> [--delimiter ,] [--output markdown|json] [--outlier-z 3.0]
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path


# ---------- type inference ----------

def _try_numeric(values):
    """Return (is_numeric, floats_or_none_list)."""
    parsed = []
    for v in values:
        if v == "":
            parsed.append(None)
            continue
        try:
            parsed.append(float(v))
        except ValueError:
            return False, []
    return True, parsed


def infer_type(values):
    """Infer column type from a list of raw string values."""
    non_empty = [v for v in values if v != ""]
    if not non_empty:
        return "empty"
    is_num, _ = _try_numeric(non_empty)
    if is_num:
        if all("." not in v for v in non_empty):
            return "integer"
        return "float"
    return "string"


# ---------- statistics ----------

def numeric_stats(floats):
    """Return dict of basic stats for a list that may contain None."""
    vals = [v for v in floats if v is not None]
    if not vals:
        return {}
    n = len(vals)
    mean = sum(vals) / n
    variance = sum((x - mean) ** 2 for x in vals) / n
    std = math.sqrt(variance)
    return {
        "min": min(vals),
        "max": max(vals),
        "mean": round(mean, 4),
        "std": round(std, 4),
    }


def outlier_indices(floats, z_threshold):
    """Return list of (original_index, value) where |z| > threshold."""
    vals = [v for v in floats if v is not None]
    if len(vals) < 4:
        return []
    mean = sum(vals) / len(vals)
    variance = sum((x - mean) ** 2 for x in vals) / len(vals)
    std = math.sqrt(variance)
    if std == 0:
        return []
    results = []
    for i, v in enumerate(floats):
        if v is not None and abs((v - mean) / std) > z_threshold:
            results.append((i, v))
    return results


def top_values(raw_values, k=5):
    """Return top-k (value, count) pairs for a column, excluding empty."""
    counts = Counter(v for v in raw_values if v != "")
    return counts.most_common(k)


# ---------- profiling ----------

def profile(path, delimiter, outlier_z):
    path = Path(path)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if reader.fieldnames is None:
            print("ERROR: Could not read CSV headers.", file=sys.stderr)
            sys.exit(1)
        headers = list(reader.fieldnames)
        rows = list(reader)

    total_rows = len(rows)
    total_cols = len(headers)

    # Build column data
    col_data = {h: [row.get(h, "") for row in rows] for h in headers}

    # Duplicate rows (compare raw dicts)
    row_tuples = [tuple(row.get(h, "") for h in headers) for row in rows]
    duplicate_rows = total_rows - len(set(row_tuples))

    total_nulls = sum(1 for h in headers for v in col_data[h] if v == "")

    columns = []
    for h in headers:
        vals = col_data[h]
        null_count = sum(1 for v in vals if v == "")
        null_pct = round(100 * null_count / total_rows, 1) if total_rows else 0
        unique_count = len(set(v for v in vals if v != ""))
        unique_pct = round(100 * unique_count / (total_rows - null_count), 1) if (total_rows - null_count) else 0
        dtype = infer_type(vals)

        col = {
            "name": h,
            "type": dtype,
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": unique_count,
            "unique_pct": unique_pct,
        }

        if dtype in ("integer", "float"):
            _, floats = _try_numeric(vals)
            stats = numeric_stats(floats)
            col.update(stats)
            outliers = outlier_indices(floats, outlier_z)
            col["outlier_count"] = len(outliers)
            col["outlier_samples"] = outliers[:5]  # cap at 5 for readability
        else:
            col["top_values"] = top_values(vals)

        columns.append(col)

    return {
        "file": str(path),
        "total_rows": total_rows,
        "total_cols": total_cols,
        "duplicate_rows": duplicate_rows,
        "total_null_cells": total_nulls,
        "columns": columns,
    }


# ---------- formatting ----------

def _md_table(headers, rows):
    col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    head = "| " + " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    lines = [head, sep]
    for row in rows:
        lines.append("| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) + " |")
    return "\n".join(lines)


def render_markdown(data):
    lines = []
    lines.append(f"# CSV Profile: `{data['file']}`\n")
    lines.append("## Summary\n")
    summary_rows = [
        ["Total rows", data["total_rows"]],
        ["Total columns", data["total_cols"]],
        ["Duplicate rows", data["duplicate_rows"]],
        ["Total null cells", data["total_null_cells"]],
    ]
    lines.append(_md_table(["Metric", "Value"], summary_rows))
    lines.append("")

    lines.append("## Column Profile\n")
    col_headers = ["Column", "Type", "Nulls", "Null %", "Unique", "Unique %", "Min", "Max", "Mean", "Std", "Outliers"]
    col_rows = []
    for c in data["columns"]:
        col_rows.append([
            c["name"],
            c["type"],
            c["null_count"],
            f"{c['null_pct']}%",
            c["unique_count"],
            f"{c['unique_pct']}%",
            c.get("min", "—"),
            c.get("max", "—"),
            c.get("mean", "—"),
            c.get("std", "—"),
            c.get("outlier_count", "—"),
        ])
    lines.append(_md_table(col_headers, col_rows))
    lines.append("")

    # Top values for string columns
    string_cols = [c for c in data["columns"] if "top_values" in c]
    if string_cols:
        lines.append("## Top Values (String/Categorical Columns)\n")
        for c in string_cols:
            lines.append(f"**{c['name']}**")
            if c["top_values"]:
                tv_rows = [[v, cnt] for v, cnt in c["top_values"]]
                lines.append(_md_table(["Value", "Count"], tv_rows))
            else:
                lines.append("_(all empty)_")
            lines.append("")

    # Outlier details for numeric columns
    numeric_outlier_cols = [c for c in data["columns"] if c.get("outlier_count", 0) > 0]
    if numeric_outlier_cols:
        lines.append("## Outlier Detail (z-score flagged)\n")
        for c in numeric_outlier_cols:
            lines.append(f"**{c['name']}** — {c['outlier_count']} outlier(s)")
            if c["outlier_samples"]:
                o_rows = [[f"row {i}", v] for i, v in c["outlier_samples"]]
                lines.append(_md_table(["Location", "Value"], o_rows))
            lines.append("")

    return "\n".join(lines)


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description="Profile a CSV file for data quality.")
    parser.add_argument("path", help="Path to the CSV file")
    parser.add_argument("--delimiter", default=",", help="Column delimiter (default: comma)")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--outlier-z", type=float, default=3.0, dest="outlier_z",
                        help="Z-score threshold for outlier detection (default: 3.0)")
    args = parser.parse_args()

    data = profile(args.path, args.delimiter, args.outlier_z)

    if args.output == "json":
        print(json.dumps(data, indent=2))
    else:
        print(render_markdown(data))


if __name__ == "__main__":
    main()
