# HW5: csv-profiler Skill

## Video Walkthrough

> **[Video Walkthrough](https://youtu.be/eMAeNV20vdw)**

---

## What the skill does

`csv-profiler` analyzes any CSV file and produces a structured data quality report. In a single command it tells you:

- How many rows and columns exist, and how many are duplicates
- Each column's inferred type (integer, float, string, empty)
- Null count and null percentage per column
- Unique value count and uniqueness rate
- Min, max, mean, and standard deviation for numeric columns
- Outlier detection via z-score for every numeric column
- Top-5 most frequent values for categorical/string columns

The agent then interprets the output — flagging high-null columns, suspicious outliers, and type mismatches — and suggests concrete next steps.

---

## Why I chose this task

A language model cannot reliably profile a CSV from raw text alone:

- It cannot count 25,000 rows accurately
- It cannot compute a precise mean or standard deviation
- It cannot reliably detect outliers without arithmetic
- It will hallucinate type inferences for ambiguous mixed-type columns

This makes `csv-profiler` a clear case where **the script is genuinely load-bearing**, not decorative. The model's job is to orchestrate the script and interpret its output — not to do the math itself.

---

## Skill structure

```
.agents/
└─ skills/
   └─ csv-profiler/
      ├─ SKILL.md                  # Activation logic, instructions, I/O spec
      └─ scripts/
         └─ profile_csv.py         # The deterministic profiling engine
sample_data/
└─ employees.csv                   # Demo dataset for testing
README.md
```

---

## How to use it

### Prerequisites

Python 3.7+ (no third-party dependencies — uses only the standard library).

### Run the script directly

```bash
# Markdown output (default)
python .agents/skills/csv-profiler/scripts/profile_csv.py sample_data/employees.csv

# JSON output (for piping into other tools)
python .agents/skills/csv-profiler/scripts/profile_csv.py sample_data/employees.csv --output json

# Tab-delimited file
python .agents/skills/csv-profiler/scripts/profile_csv.py data.tsv --delimiter $'\t'

# Tighter outlier threshold
python .agents/skills/csv-profiler/scripts/profile_csv.py data.csv --outlier-z 2.0
```

### Invoke via agent (Claude Code)

Just describe the task naturally:

> "Profile employees.csv for data quality issues."
> "Audit this CSV before I load it into Postgres."
> "Are there any missing values or outliers in my data?"

The agent reads the `csv-profiler` skill description, runs the script, and returns an interpreted report with suggested next steps.

---

## What the script does

`profile_csv.py` is a self-contained, zero-dependency Python script that:

1. **Reads** the CSV using `csv.DictReader` with UTF-8-sig encoding (handles BOM)
2. **Infers types** column by column: tries to parse all non-empty values as float; if successful, checks whether any contain a decimal point to distinguish integer from float; otherwise marks as string
3. **Computes statistics**: for numeric columns — min, max, mean, std; for string columns — top-k value frequency via `Counter`
4. **Detects outliers** using z-score: flags rows where `|value − mean| / std > threshold` (default 3.0)
5. **Counts duplicates** by comparing full row tuples in a set
6. **Renders output** as a formatted Markdown report (or JSON if `--output json`)

Everything is deterministic and reproducible — the same file always produces the same report.

---

## Test cases demonstrated

| Case | Description | What to look for |
|------|-------------|-----------------|
| Normal | `employees.csv` (25 rows, 8 cols, mixed types) | Outlier salary ($450k), 4 missing emails, correct type inference |
| Edge | Header-only CSV (0 data rows) | Graceful "empty" type report, no crash |
| Error | Non-existent file path | Clear error message to stderr, non-zero exit code |

---

## What worked well

- **Zero dependencies**: the script runs anywhere Python 3.7+ is installed — no `pip install` needed
- **Outlier detection caught a real issue**: Rachel's $450,000 salary (vs. ~$80k average) was immediately flagged
- **Type inference is practical**: the heuristic correctly identified integers vs. floats vs. strings without needing pandas
- **JSON mode** makes the output composable — you can pipe it into `jq` or another script for downstream processing

## Limitations

- Loads the entire file into memory; files over ~500 MB may be slow or cause OOM
- Type inference is heuristic: a column like `"1", "2", "N/A"` will be typed as string because `"N/A"` fails float parsing
- Outlier detection is z-score only — not meaningful for ID columns or free-text fields
- Date/time columns are treated as strings; no temporal analysis is performed
- The skill does not modify or clean the data — profiling only
