---
name: csv-profiler
description: Analyzes a CSV file and produces a structured data quality profile covering row counts, column types, null rates, uniqueness, numeric statistics, outlier flags, and top categorical values. Use when the user asks to inspect, audit, profile, or understand a CSV dataset before cleaning, analysis, or import. Do NOT use for non-CSV files or when the user only wants to query specific values from a dataset.
---

## When to use this skill

Use `csv-profiler` when the user wants to:
- Understand what is in a CSV file they have not seen before
- Check data quality before loading into a database or pipeline
- Audit for missing values, duplicate rows, or suspicious outliers
- Get column-level statistics and type information quickly

## When NOT to use this skill

- The file is not a CSV (use a different skill or tool for Excel, JSON, Parquet, etc.)
- The user wants to query specific records or filter rows (use pandas or SQL instead)
- The file is too sensitive to pass to a script (remind the user and stop)
- The user only wants help writing code that reads CSVs (just write the code)

## Expected inputs

- A path to a CSV file (local path or stdin-piped content)
- Optional: `--delimiter` flag if not comma-separated (e.g., tab-delimited TSV)
- Optional: `--output` flag for `json` or `markdown` (default: `markdown`)
- Optional: `--outlier-z` flag for z-score outlier threshold (default: 3.0)

## Step-by-step instructions

1. **Confirm the file exists.** If the user did not provide a path, ask for one before proceeding.
2. **Run the script.** Execute:
   ```
   python .agents/skills/csv-profiler/scripts/profile_csv.py <path> [--output markdown|json] [--delimiter ,] [--outlier-z 3.0]
   ```
3. **Read the output.** The script prints a full profile to stdout.
4. **Interpret and narrate.** Summarize the most important findings:
   - Flag any columns with high null rates (>10%)
   - Call out columns where all values are unique (possible ID columns)
   - Mention outlier-flagged columns by name
   - Note any columns where the inferred type conflicts with the column name (e.g., a column named `age` that parsed as string)
5. **Suggest next steps.** Offer 2–3 concrete actions based on what you found (e.g., "Column `email` has 23% nulls — consider dropping or imputing before training").

## Expected output format

The markdown report produced by the script includes:

- **Summary table**: total rows, columns, duplicate rows, total null cells
- **Per-column table**: inferred type, null count, null %, unique count, unique %, and for numerics: min, max, mean, std, outlier count
- **Top values section**: for string/categorical columns, the 5 most frequent values and their counts
- **Outlier detail**: for flagged numeric columns, the row indices and values that exceed the z-score threshold

After printing the script output verbatim, add a short "Key Findings" section in plain prose (3–6 bullets).

## Limitations and checks

- The script loads the entire file into memory. Files larger than ~500 MB may be slow or fail; warn the user if the file is large.
- Type inference is heuristic: a column of `"1", "2", "N/A"` may be inferred as string. Mention this caveat when types look surprising.
- Outlier detection uses z-score on numeric columns only; it is not meaningful for IDs or free-text fields.
- Do not attempt to fix or clean the data as part of this skill. Profiling only — refer the user to a separate cleaning step.
