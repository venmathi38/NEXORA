"""
NEXORA AI — Smart Data Cleaning Engine

This module ONLY analyses and suggests fixes. It never modifies the
uploaded dataset automatically. The caller (main.py) must:
    1. Call analyze_dataset(df)      → get the cleaning report
    2. Show it to the user           → wait for confirmation
    3. Call apply_fixes(df, fixes)   → get a cleaned copy
"""

import re

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _is_missing(value):
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip() == ""


def _looks_numeric_column(series):
    non_missing = series.dropna().astype("string").str.strip()
    non_missing = non_missing[non_missing.ne("")]
    if non_missing.empty:
        return False

    cleaned = non_missing.str.replace(r"[,$€£₹\s]", "", regex=True)
    cleaned = cleaned.str.replace(r"[()]", "", regex=True)
    parsed = pd.to_numeric(cleaned, errors="coerce")
    return parsed.notna().mean() >= 0.7


def _looks_date_column(column_name, series):
    name = str(column_name).lower()
    if any(kw in name for kw in ("date", "expiry", "received", "order")):
        return True

    non_missing = series.dropna().astype("string").str.strip()
    non_missing = non_missing[non_missing.ne("")]
    if non_missing.empty:
        return False

    sample = non_missing.head(50)
    pattern = r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}"
    matched = sample.str.match(pattern, na=False).mean()
    return matched >= 0.7


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def analyze_dataset(df):
    """
    Read-only inspection of a DataFrame.
    Returns a report describing every issue found, with suggested fixes.
    """
    if df is None or df.empty:
        return {
            "available": False,
            "message": "Dataset is empty.",
            "issues": [],
            "total_issues": 0,
        }

    issues = []

    # 1. Duplicate rows
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        issues.append({
            "id": "duplicates",
            "type": "duplicate_rows",
            "severity": "warning",
            "title": "Duplicate rows detected",
            "detail": (
                f"{duplicate_count} fully duplicate row(s) found. "
                "Applying this fix will keep only the first occurrence."
            ),
            "count": duplicate_count,
            "fixable": True,
        })

    # 2. Column-by-column inspection
    for column in df.columns:
        series = df[column]

        # 2a. Missing values
        missing_mask = series.map(_is_missing)
        missing_count = int(missing_mask.sum())
        if missing_count:
            missing_pct = round(missing_count / len(series) * 100, 2)
            strategy = "drop_rows" if missing_pct >= 50 else "fill_placeholder"
            issues.append({
                "id": f"missing::{column}",
                "type": "missing_values",
                "column": column,
                "severity": "warning",
                "title": f"Missing values in '{column}'",
                "detail": (
                    f"{missing_count} missing value(s) ({missing_pct}%). "
                    "Suggestion: drop rows if >50% missing, "
                    "otherwise fill with a placeholder."
                ),
                "count": missing_count,
                "percentage": missing_pct,
                "fixable": True,
                "suggested_strategy": strategy,
            })

        # 2b. Whitespace around text values
        if series.dtype == object:
            text = series.dropna().astype("string")
            with_extra_space = text[text.ne(text.str.strip())]
            if len(with_extra_space):
                issues.append({
                    "id": f"whitespace::{column}",
                    "type": "extra_whitespace",
                    "column": column,
                    "severity": "info",
                    "title": f"Extra whitespace in '{column}'",
                    "detail": (
                        f"{len(with_extra_space)} value(s) have leading or "
                        "trailing spaces. Suggested fix: strip whitespace."
                    ),
                    "count": int(len(with_extra_space)),
                    "fixable": True,
                })

        # 2c. Numeric column with non-numeric values
        if _looks_numeric_column(series):
            cleaned = series.astype("string").str.strip()
            cleaned = cleaned.str.replace(r"[,$€£₹\s]", "", regex=True)
            cleaned = cleaned.str.replace(r"[()]", "", regex=True)
            parsed = pd.to_numeric(cleaned, errors="coerce")
            non_empty = series.map(lambda v: not _is_missing(v))
            invalid_mask = non_empty & parsed.isna()
            invalid_count = int(invalid_mask.sum())
            if invalid_count:
                issues.append({
                    "id": f"numeric::{column}",
                    "type": "invalid_numeric",
                    "column": column,
                    "severity": "warning",
                    "title": f"Non-numeric values in numeric column '{column}'",
                    "detail": (
                        f"{invalid_count} value(s) could not be parsed as "
                        "numbers. Suggested fix: coerce them to empty."
                    ),
                    "count": invalid_count,
                    "fixable": True,
                })

        # 2d. Date column with invalid dates
        if _looks_date_column(column, series):
            text = series.astype("string").str.strip()
            non_empty = series.map(lambda v: not _is_missing(v))
            parsed = pd.to_datetime(text, errors="coerce", format="mixed", dayfirst=False)
            invalid_mask = non_empty & parsed.isna()
            invalid_count = int(invalid_mask.sum())

            ambiguous_mask = text.str.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}$", na=False)
            ambiguous_parts = text.str.extract(r"^(\d{1,2})[/-](\d{1,2})[/-]\d{4}$")
            both_at_most_12 = (
                ambiguous_parts.notna().all(axis=1)
                & ambiguous_parts.astype(float).le(12).all(axis=1)
            )
            ambiguous_count = int((ambiguous_mask & both_at_most_12 & non_empty).sum())

            if invalid_count:
                issues.append({
                    "id": f"date_invalid::{column}",
                    "type": "invalid_date",
                    "column": column,
                    "severity": "warning",
                    "title": f"Invalid dates in '{column}'",
                    "detail": (
                        f"{invalid_count} value(s) could not be parsed as dates. "
                        "Suggested fix: coerce them to empty."
                    ),
                    "count": invalid_count,
                    "fixable": True,
                })

            if ambiguous_count:
                issues.append({
                    "id": f"date_ambiguous::{column}",
                    "type": "ambiguous_date",
                    "column": column,
                    "severity": "info",
                    "title": f"Ambiguous dates in '{column}'",
                    "detail": (
                        f"{ambiguous_count} date(s) could be day-first or month-first. "
                        "NEXORA does NOT auto-fix these — please review manually."
                    ),
                    "count": ambiguous_count,
                    "fixable": False,
                })

        # 2e. Outliers on numeric columns (IQR)
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if len(clean) >= 10:
                q1 = clean.quantile(0.25)
                q3 = clean.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    low = q1 - 1.5 * iqr
                    high = q3 + 1.5 * iqr
                    outlier_mask = (series < low) | (series > high)
                    outlier_count = int(outlier_mask.sum())
                    if outlier_count:
                        issues.append({
                            "id": f"outliers::{column}",
                            "type": "outlier",
                            "column": column,
                            "severity": "info",
                            "title": f"Possible outliers in '{column}'",
                            "detail": (
                                f"{outlier_count} value(s) outside 1.5×IQR range. "
                                "Review manually — these are NOT auto-fixed."
                            ),
                            "count": outlier_count,
                            "fixable": False,
                        })

    return {
        "available": True,
        "message": "Analysis complete. No changes were applied.",
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "total_issues": len(issues),
        "issues": issues,
        "original_preview": _safe_preview(df, 5),
    }


def apply_fixes(df, fix_ids):
    """
    Return a NEW cleaned DataFrame containing only the requested fixes.
    The original df is never modified.
    """
    if df is None or df.empty:
        return df

    if not isinstance(fix_ids, (list, tuple)):
        fix_ids = []

    fix_set = set(fix_ids)
    cleaned = df.copy()
    applied = []

    # Duplicate rows
    if "duplicates" in fix_set:
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        applied.append({
            "fix": "duplicates",
            "removed_rows": before - len(cleaned),
        })

    for column in cleaned.columns:
        series = cleaned[column]

        # Whitespace
        if f"whitespace::{column}" in fix_set and series.dtype == object:
            cleaned[column] = series.map(
                lambda v: v.strip() if isinstance(v, str) else v
            )
            applied.append({"fix": f"whitespace::{column}"})

        # Missing values
        if f"missing::{column}" in fix_set:
            missing_mask = series.map(_is_missing)
            missing_pct = missing_mask.mean() * 100
            if missing_pct >= 50:
                cleaned = cleaned.loc[~missing_mask].reset_index(drop=True)
                applied.append({
                    "fix": f"missing::{column}",
                    "strategy": "drop_rows",
                })
            else:
                cleaned[column] = series.where(~missing_mask, "")
                applied.append({
                    "fix": f"missing::{column}",
                    "strategy": "fill_placeholder",
                })

        # Invalid numeric values
        if f"numeric::{column}" in fix_set:
            text = cleaned[column].astype("string").str.strip()
            text = text.str.replace(r"[,$€£₹\s]", "", regex=True)
            text = text.str.replace(r"[()]", "", regex=True)
            parsed = pd.to_numeric(text, errors="coerce")
            cleaned[column] = parsed
            applied.append({"fix": f"numeric::{column}"})

        # Invalid dates
        if f"date_invalid::{column}" in fix_set:
            text = cleaned[column].astype("string").str.strip()
            parsed = pd.to_datetime(
                text, errors="coerce", format="mixed", dayfirst=False
            )
            cleaned[column] = parsed.dt.strftime("%Y-%m-%d")
            applied.append({"fix": f"date_invalid::{column}"})

    return {
        "cleaned": cleaned,
        "applied": applied,
        "original_rows": int(len(df)),
        "cleaned_rows": int(len(cleaned)),
    }


def to_csv_bytes(df):
    """Serialize a DataFrame to UTF-8 CSV bytes for download."""
    if df is None:
        return b""
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------------
# Internal preview helper
# ---------------------------------------------------------------------
def _safe_preview(df, n):
    if df is None or df.empty:
        return []
    head = df.head(n).astype(object)
    head = head.where(pd.notna(head), None)
    return head.to_dict(orient="records")


# =====================================================================
# EXCEL EXPORT — cleaned dataset with formatting
# =====================================================================
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io as _io


GOLD_HEX = "D8BD83"
DARK_HEX = "1A2233"
LIGHT_GOLD_HEX = "F5EDD9"
RED_HEX = "E17C83"
TEAL_HEX = "58B9AA"
WHITE_HEX = "FFFFFF"
GREY_HEX = "F2F2F2"


def _apply_header_style(ws, row=1, bg=GOLD_HEX):
    for cell in ws[row]:
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor=bg)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        thin = Side(border_style="thin", color=WHITE_HEX)
        cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws.row_dimensions[row].height = 22


def _auto_width(ws, max_width=50):
    for column_cells in ws.columns:
        length = 0
        letter = None
        for cell in column_cells:
            try:
                if cell.value:
                    length = max(length, len(str(cell.value)))
                letter = cell.column_letter
            except AttributeError:
                pass
        if letter:
            ws.column_dimensions[letter].width = min(max_width, max(10, length + 2))


def export_cleaned_excel(df, auto_fix=True):
    """
    Produce an .xlsx file with:
      Sheet 1 — Cleaned Data (all fixes auto-applied)
      Sheet 2 — Cleaning Summary (issues found + applied fixes)
      Sheet 3 — Original vs Cleaned Comparison (row counts, duplicates, missing)
    Returns bytes ready for HTTP download.
    """
    original_df = df.copy()
    fixes_applied = []

    # --- 1. Analyse first ---
    report = analyze_dataset(original_df)

    # --- 2. Apply all fixable fixes automatically ---
    if auto_fix and report.get("available"):
        fix_ids = [
            issue["id"] for issue in report.get("issues", [])
            if issue.get("fixable")
        ]
        if fix_ids:
            result = apply_fixes(original_df, fix_ids)
            cleaned_df = result["cleaned"]
            fixes_applied = result["applied"]
        else:
            cleaned_df = original_df.copy()
    else:
        cleaned_df = original_df.copy()

    # --- 3. Build workbook ---
    wb = Workbook()

    # Sheet 1 — Cleaned Data
    ws1 = wb.active
    ws1.title = "Cleaned Data"

    ws1.append([f"NEXORA AI — Cleaned Dataset  ·  {len(cleaned_df)} rows × {len(cleaned_df.columns)} columns"])
    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cleaned_df.columns))
    ws1.cell(row=1, column=1).font = Font(bold=True, size=13, color="FFFFFF")
    ws1.cell(row=1, column=1).fill = PatternFill("solid", fgColor=DARK_HEX)
    ws1.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 28

    ws1.append(list(cleaned_df.columns))
    _apply_header_style(ws1, row=2, bg=GOLD_HEX)

    for row in cleaned_df.itertuples(index=False):
        ws1.append(list(row))

    # Alternate row shading
    for i, row in enumerate(ws1.iter_rows(min_row=3, max_row=ws1.max_row)):
        for cell in row:
            if i % 2 == 1:
                cell.fill = PatternFill("solid", fgColor=GREY_HEX)
            cell.alignment = Alignment(vertical="center")

    ws1.freeze_panes = "A3"
    _auto_width(ws1)

    # Sheet 2 — Cleaning Summary
    ws2 = wb.create_sheet("Cleaning Summary")
    ws2.append(["NEXORA AI — Cleaning Summary"])
    ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
    ws2.cell(row=1, column=1).font = Font(bold=True, size=13, color="FFFFFF")
    ws2.cell(row=1, column=1).fill = PatternFill("solid", fgColor=DARK_HEX)
    ws2.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 28

    ws2.append([])
    ws2.append(["Total issues found:", report.get("total_issues", 0)])
    ws2.append(["Total rows (original):", len(original_df)])
    ws2.append(["Total rows (cleaned):", len(cleaned_df)])
    ws2.append(["Rows removed:", max(0, len(original_df) - len(cleaned_df))])
    ws2.append(["Fixes applied:", len(fixes_applied)])

    for row in ws2.iter_rows(min_row=3, max_row=7):
        row[0].font = Font(bold=True)
        row[0].fill = PatternFill("solid", fgColor=LIGHT_GOLD_HEX)

    ws2.append([])
    ws2.append(["", "Severity", "Column", "Title", "Detail", "Fixable"])

    for cell in ws2[ws2.max_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=GOLD_HEX)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for issue in report.get("issues", []):
        ws2.append([
            "",
            issue.get("severity", "").upper(),
            issue.get("column", "—"),
            issue.get("title", ""),
            issue.get("detail", ""),
            "Yes" if issue.get("fixable") else "Manual",
        ])
        last_row = ws2.max_row
        severity = issue.get("severity", "")
        bg = {
            "warning": "FFE5CC",
            "danger": "FFD0D4",
            "info": "D4F0EC",
        }.get(severity, GREY_HEX)
        ws2.cell(row=last_row, column=2).fill = PatternFill("solid", fgColor=bg)
        ws2.cell(row=last_row, column=2).alignment = Alignment(horizontal="center")

    _auto_width(ws2)

    # Sheet 3 — Comparison
    ws3 = wb.create_sheet("Original vs Cleaned")
    ws3.append(["Metric", "Original", "Cleaned", "Change"])
    for cell in ws3[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=GOLD_HEX)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 22

    orig_missing = int(original_df.isna().sum().sum())
    clean_missing = int(cleaned_df.isna().sum().sum())
    orig_dup = int(original_df.duplicated().sum())
    clean_dup = int(cleaned_df.duplicated().sum())

    metrics = [
        ("Rows", len(original_df), len(cleaned_df)),
        ("Columns", len(original_df.columns), len(cleaned_df.columns)),
        ("Missing cells", orig_missing, clean_missing),
        ("Duplicate rows", orig_dup, clean_dup),
    ]
    for label, orig, clean in metrics:
        change = clean - orig
        ws3.append([label, orig, clean, f"{change:+d}" if change != 0 else "0"])
        last = ws3.max_row
        if change > 0:
            ws3.cell(row=last, column=4).fill = PatternFill("solid", fgColor="FFD0D4")
        elif change < 0:
            ws3.cell(row=last, column=4).fill = PatternFill("solid", fgColor="D4F0EC")

    _auto_width(ws3)

    # --- 4. Serialize ---
    buffer = _io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()