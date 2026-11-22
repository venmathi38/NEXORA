import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# NEXORA AI configuration
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DATASET = DATA_DIR / "Sales_Dataset.csv"

COLUMN_ALIASES = {
    "product": ["Product_Name", "Product", "Product Name"],
    "product_id": ["Product_ID", "Product ID", "ID"],
    "category": ["Category", "Catagory", "Product_Category"],
    "stock": ["Stock_Quantity", "Stock Quantity", "Stock"],
    "reorder_level": ["Reorder_Level", "Reorder Level"],
    "reorder_quantity": ["Reorder_Quantity", "Reorder Quantity"],
    "price": ["Unit_Price", "Unit Price", "Price"],
    "currency": ["Currency", "Currency_Code", "Currency Code"],
    "sales": ["Sales_Volume", "Sales Volume", "Sales"],
    "turnover": ["Inventory_Turnover_Rate", "Inventory Turnover Rate", "Turnover"],
    "expiry": ["Expiration_Date", "Expiry_Date", "Expiry Date"],
    "received": ["Date_Received", "Date Received"],
    "last_order": ["Last_Order_Date", "Last Order Date"],
    "supplier": ["Supplier_Name", "Supplier Name"],
    "location": ["Warehouse_Location", "Warehouse Location"],
    "status": ["Status", "Product_Status"],
}

DATE_KEYS = ("expiry", "received", "last_order")


# ---------------------------------------------------------------------
# General data helpers
# ---------------------------------------------------------------------
def find_column(df, key):
    """Find a dataset column using known alternative names."""
    if df is None or not hasattr(df, "columns"):
        return None

    normalized = {str(column).strip().casefold(): column for column in df.columns}
    for alias in COLUMN_ALIASES.get(key, []):
        found = normalized.get(alias.strip().casefold())
        if found is not None:
            return found
    return None


def load_data(file_path=None):
    """Load CSV/Excel data without changing it or deleting rows."""
    path = Path(file_path) if file_path else DEFAULT_DATASET

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    extension = path.suffix.lower()

    if extension == ".csv":
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin-1")

    elif extension in (".xlsx", ".xls"):
        df = pd.read_excel(path)

    else:
        raise ValueError(
            "Unsupported file format. Please upload CSV or Excel."
        )

    if df.empty:
        raise ValueError("The uploaded dataset is empty.")

    df.columns = [str(column).strip() for column in df.columns]

    if df.columns.duplicated().any():
        duplicates = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(
            f"Duplicate column names found after trimming spaces: {duplicates}"
        )

    return df


def get_dataset_profile(df):
    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    return {
        "total_rows": int(df.shape[0]),
        "total_columns": int(df.shape[1]),
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "missing_percentage": (
            round(missing_cells / total_cells * 100, 2) if total_cells else 0
        ),
        "column_names": list(df.columns),
    }


def parse_numeric_series(values):
    """Parse numbers containing common currency symbols and separators."""
    cleaned = values.astype("string").str.strip()
    cleaned = cleaned.str.replace(r"[,$€£₹\s]", "", regex=True)

    negative = cleaned.str.match(r"^\(.*\)$", na=False)
    cleaned = cleaned.str.replace(r"[()]", "", regex=True)

    numbers = pd.to_numeric(cleaned, errors="coerce")
    return numbers.where(~negative, -numbers.abs())


def numeric_column(df, key):
    column = find_column(df, key)
    if column is None:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return parse_numeric_series(df[column])


def _records(df):
    """Convert DataFrame values into JSON-friendly Python values."""
    if df is None or df.empty:
        return []
    safe = df.astype(object).where(pd.notna(df), None)
    return safe.to_dict(orient="records")


# ---------------------------------------------------------------------
# KPI calculations
# ---------------------------------------------------------------------
def get_kpis(df):
    stock_col = find_column(df, "stock")
    sales_col = find_column(df, "sales")
    price_col = find_column(df, "price")
    currency_col = find_column(df, "currency")
    turnover_col = find_column(df, "turnover")
    reorder_col = find_column(df, "reorder_level")
    product_col = find_column(df, "product")

    stock = numeric_column(df, "stock")
    sales = numeric_column(df, "sales")
    price = numeric_column(df, "price")
    turnover = numeric_column(df, "turnover")
    reorder = numeric_column(df, "reorder_level")

    total_products = int(df[product_col].nunique()) if product_col else int(len(df))
    total_stock = float(stock.sum()) if stock_col else 0.0
    total_sales = float(sales.sum()) if sales_col else 0.0

    inventory_value = (
        float((stock * price).fillna(0).sum())
        if stock_col and price_col else 0.0
    )
    estimated_sales_value = (
        float((sales * price).fillna(0).sum())
        if sales_col and price_col else None
    )

    currencies = (
        df[currency_col].dropna().astype(str).str.strip()
        if currency_col else pd.Series(dtype="object")
    )
    currencies = currencies[currencies.ne("")].unique().tolist()
    currency = (
        currencies[0] if len(currencies) == 1
        else ("Mixed" if currencies else "Unknown currency")
    )

    average_turnover = (
        float(turnover.mean())
        if turnover_col and turnover.notna().any() else 0.0
    )
    low_stock_count = (
        int((stock.notna() & reorder.notna() & (stock <= reorder)).sum())
        if stock_col and reorder_col else 0
    )

    return {
        "total_products": total_products,
        "total_stock": round(total_stock, 2),
        "total_sales": round(total_sales, 2),
        "inventory_value": round(inventory_value, 2),
        "estimated_sales_value": (
            round(estimated_sales_value, 2)
            if estimated_sales_value is not None else None
        ),
        "currency": currency,
        "average_turnover": round(average_turnover, 2),
        "low_stock": low_stock_count,
    }


# ---------------------------------------------------------------------
# Stock analysis
# ---------------------------------------------------------------------
def get_low_stock(df):
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder_level")
    if stock_col is None or reorder_col is None:
        return []

    stock = numeric_column(df, "stock")
    reorder = numeric_column(df, "reorder_level")
    mask = stock.notna() & reorder.notna() & (stock <= reorder)

    result = df.loc[mask].copy()
    result["_stock_sort"] = stock.loc[mask]
    result = result.sort_values("_stock_sort", ascending=True)
    return _records(result.drop(columns=["_stock_sort"]))


def get_overstock(df):
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder_level")
    if stock_col is None or reorder_col is None:
        return []

    stock = numeric_column(df, "stock")
    reorder = numeric_column(df, "reorder_level")

    mask = (
        stock.notna()
        & reorder.notna()
        & (reorder > 0)
        & (stock > 0)
        & (stock > reorder * 3)
    )
    return _records(df.loc[mask])


# ---------------------------------------------------------------------
# Date and expiry analysis
# ---------------------------------------------------------------------
def parse_date_safely(value):
    """Parse ISO and unambiguous numeric dates; reject ambiguous dates."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, (datetime, pd.Timestamp)):
        parsed = pd.Timestamp(value)
        return None if pd.isna(parsed) else parsed

    text = str(value).strip()
    if not text:
        return None

    if len(text) >= 10 and text[4] == "-":
        parsed = pd.to_datetime(text, errors="coerce", yearfirst=True)
        return None if pd.isna(parsed) else parsed

    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if match:
        first, second, year = map(int, match.groups())

        if first > 12 and 1 <= second <= 12:
            day, month = first, second
        elif second > 12 and 1 <= first <= 12:
            month, day = first, second
        else:
            return None

        parsed = pd.to_datetime(
            f"{year:04d}-{month:02d}-{day:02d}",
            format="%Y-%m-%d",
            errors="coerce",
        )
        return None if pd.isna(parsed) else parsed

    parsed = pd.to_datetime(text, errors="coerce")
    return None if pd.isna(parsed) else parsed


def classify_expiry_date(value, today=None):
    """Classify one expiry value without guessing ambiguous numeric dates."""
    if value is None or pd.isna(value) or not str(value).strip():
        return "Missing", None

    text = str(value).strip()
    numeric_date = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if numeric_date:
        first = int(numeric_date.group(1))
        second = int(numeric_date.group(2))
        if first <= 12 and second <= 12:
            return "Ambiguous", None

    expiry_date = parse_date_safely(value)
    if expiry_date is None:
        return "Invalid", None

    current_date = (
        pd.Timestamp(today).normalize()
        if today is not None else pd.Timestamp.today().normalize()
    )
    days_left = int((expiry_date.normalize() - current_date).days)

    if days_left < 0:
        status = "Expired"
    elif days_left <= 7:
        status = "Expiring within 7 days"
    elif days_left <= 30:
        status = "Expiring within 30 days"
    else:
        status = "Valid"

    return status, days_left


def get_expiry_analysis(df, today=None):
    expiry_col = find_column(df, "expiry")
    if expiry_col is None:
        return {"available": False, "counts": {}, "records": []}

    status_names = (
        "Expired",
        "Expiring within 7 days",
        "Expiring within 30 days",
        "Valid",
        "Ambiguous",
        "Missing",
        "Invalid",
    )
    counts = {name: 0 for name in status_names}
    records = []

    for _, row in df.iterrows():
        status, days_left = classify_expiry_date(row[expiry_col], today=today)
        counts[status] += 1
        item = row.to_dict()
        item["expiry_status"] = status
        item["days_until_expiry"] = days_left
        records.append(item)

    return {
        "available": True,
        "counts": counts,
        "records": _records(pd.DataFrame(records)),
    }


def get_expiry_alerts(df):
    analysis = get_expiry_analysis(df)
    alert_statuses = {
        "Expired",
        "Expiring within 7 days",
        "Expiring within 30 days",
    }
    return [
        record for record in analysis["records"]
        if record["expiry_status"] in alert_statuses
    ]


# ---------------------------------------------------------------------
# Sales, category and supplier analysis
# ---------------------------------------------------------------------
def _product_sales_ranking(df, ascending=False, limit=10):
    product_col = find_column(df, "product")
    sales_col = find_column(df, "sales")
    if product_col is None or sales_col is None:
        return []

    working = df.copy()
    working[sales_col] = parse_numeric_series(working[sales_col])
    working = working.dropna(subset=[product_col, sales_col])
    if working.empty:
        return []

    result = (
        working.groupby(product_col, dropna=False)[sales_col]
        .sum()
        .reset_index()
        .sort_values(sales_col, ascending=ascending)
        .head(max(0, int(limit)))
    )
    return _records(result)


def get_top_selling_products(df, limit=10):
    return _product_sales_ranking(df, ascending=False, limit=limit)


def get_low_selling_products(df, limit=10):
    return _product_sales_ranking(df, ascending=True, limit=limit)


def get_category_analysis(df):
    category_col = find_column(df, "category")
    sales_col = find_column(df, "sales")
    stock_col = find_column(df, "stock")

    if category_col is None:
        return []

    working = df.copy()
    aggregations = {}

    if sales_col:
        working[sales_col] = parse_numeric_series(working[sales_col])
        aggregations[sales_col] = "sum"

    if stock_col:
        working[stock_col] = parse_numeric_series(working[stock_col])
        aggregations[stock_col] = "sum"

    if not aggregations:
        return []

    result = (
        working.groupby(category_col, dropna=False)
        .agg(aggregations)
        .reset_index()
    )
    return _records(result)


def get_supplier_analysis(df):
    supplier_col = find_column(df, "supplier")
    stock_col = find_column(df, "stock")
    if supplier_col is None:
        return []

    working = df.copy()
    if stock_col:
        working[stock_col] = parse_numeric_series(working[stock_col])
        result = (
            working.groupby(supplier_col, dropna=False)
            .agg(
                total_products=(supplier_col, "size"),
                total_stock=(stock_col, "sum"),
            )
            .reset_index()
        )
    else:
        result = (
            working.groupby(supplier_col, dropna=False)
            .size()
            .reset_index(name="total_products")
        )

    return _records(result)


# ---------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------
def get_sales_trend(df, date_key="received"):
    """Daily aggregated sales volume using Date_Received (fallback: Last_Order)."""
    sales_col = find_column(df, "sales")
    date_col = find_column(df, date_key)

    if sales_col is None or date_col is None:
        return {"available": False, "message": "Sales or date column missing."}

    working = df[[date_col, sales_col]].copy()
    working[sales_col] = parse_numeric_series(working[sales_col])
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna()

    if working.empty:
        return {"available": False, "message": "No valid dated sales rows."}

    trend = (
        working.groupby(working[date_col].dt.date)[sales_col].sum()
        .sort_index()
    )

    return {
        "available": True,
        "series": [
            {"date": str(d), "value": float(v)} for d, v in trend.items()
        ],
    }


def get_inventory_trend(df):
    """Daily aggregated stock quantity using Date_Received."""
    stock_col = find_column(df, "stock")
    date_col = find_column(df, "received")
    if stock_col is None or date_col is None:
        return {"available": False, "message": "Stock or date column missing."}

    working = df[[date_col, stock_col]].copy()
    working[stock_col] = parse_numeric_series(working[stock_col])
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna()

    if working.empty:
        return {"available": False, "message": "No valid dated stock rows."}

    trend = (
        working.groupby(working[date_col].dt.date)[stock_col].sum()
        .sort_index()
    )

    return {
        "available": True,
        "series": [
            {"date": str(d), "value": float(v)} for d, v in trend.items()
        ],
    }


# ---------------------------------------------------------------------
# Composite business score (0-100)
# ---------------------------------------------------------------------
def get_business_score(df):
    """Weighted composite: low-stock %, overstock %, expiry risk %."""
    total = int(len(df))

    if total == 0:
        return {"available": False, "message": "Empty dataset."}

    low = get_low_stock(df)
    over = get_overstock(df)

    expiry_col = find_column(df, "expiry")
    expiry_risk = 0
    if expiry_col is not None:
        expiry_risk = len(get_expiry_alerts(df))

    low_pct = len(low) / total
    over_pct = len(over) / total
    expiry_pct = expiry_risk / total

    score = 100.0
    score -= low_pct * 100 * 0.4
    score -= over_pct * 100 * 0.2
    score -= expiry_pct * 100 * 0.4
    score = max(0.0, min(100.0, score))

    return {
        "available": True,
        "score": round(score, 2),
        "components": {
            "low_stock_ratio": round(low_pct, 4),
            "overstock_ratio": round(over_pct, 4),
            "expiry_risk_ratio": round(expiry_pct, 4),
        },
    }


# ---------------------------------------------------------------------
# Data quality analysis
# ---------------------------------------------------------------------
def get_column_quality(df):
    """Return a quality summary for each column without changing the data."""
    quality = []

    for column in df.columns:
        values = df[column]
        missing = values.isna() | values.astype("string").str.strip().eq("")
        non_missing = values[~missing]
        item = {
            "column": str(column),
            "data_type": str(values.dtype),
            "total_values": int(len(values)),
            "missing_values": int(missing.sum()),
            "missing_percentage": (
                round(float(missing.mean() * 100), 2) if len(values) else 0.0
            ),
            "unique_values": int(non_missing.nunique(dropna=True)),
            "invalid_values": 0,
            "ambiguous_dates": 0,
        }

        for key in DATE_KEYS:
            if find_column(df, key) == column:
                text_values = values.astype("string").str.strip()
                date_pattern = r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}$"
                numeric_dates = text_values.str.match(date_pattern, na=False)
                parts = text_values.str.extract(
                    r"^(\d{1,2})[/-](\d{1,2})[/-]\d{4}$"
                )
                both_at_most_12 = (
                    parts.notna().all(axis=1)
                    & parts.astype(float).le(12).all(axis=1)
                )
                ambiguous = numeric_dates & both_at_most_12 & ~missing
                parsed = values.map(parse_date_safely)

                item["invalid_values"] = int(
                    (~missing & parsed.isna() & ~ambiguous).sum()
                )
                item["ambiguous_dates"] = int(ambiguous.sum())
                break

        quality.append(item)

    return quality


def get_data_quality(df):
    """Return overall and per-column data-quality information."""
    profile = get_dataset_profile(df)
    return {
        **profile,
        "columns": get_column_quality(df),
    }


# ---------------------------------------------------------------------
# Recommendations and product lookup
# ---------------------------------------------------------------------
def get_recommendations(df):
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder_level")
    product_col = find_column(df, "product")

    if stock_col is None or reorder_col is None:
        return [
            "Stock and reorder-level columns are required for inventory recommendations."
        ]

    stock = numeric_column(df, "stock")
    reorder = numeric_column(df, "reorder_level")
    valid = stock.notna() & reorder.notna()

    low_count = int((valid & (stock <= reorder)).sum())
    over_count = int((valid & (reorder > 0) & (stock > reorder * 3)).sum())
    recommendations = []

    if low_count:
        recommendations.append(
            f"{low_count} products have reached or fallen below their reorder level. "
            "Review replenishment."
        )
    else:
        recommendations.append(
            "No products are currently at or below their recorded reorder level."
        )

    if over_count:
        recommendations.append(
            f"{over_count} products have stock more than three times their reorder "
            "level. Review overstock."
        )
    else:
        recommendations.append("No products meet the current overstock rule.")

    if find_column(df, "expiry") is not None:
        expiry_count = len(get_expiry_alerts(df))
        if expiry_count:
            recommendations.append(
                f"{expiry_count} products have expired or may expire within 30 days. "
                "Verify their expiry dates."
            )
    else:
        recommendations.append(
            "Expiry recommendations are unavailable because no expiry-date column "
            "was found."
        )

    if product_col is None:
        recommendations.append(
            "Add a product-name column to enable product-level recommendations."
        )

    return recommendations


def search_product(df, product_name):
    """Find product rows using a case-insensitive partial product-name match."""
    product_col = find_column(df, "product")
    if product_col is None or product_name is None:
        return []

    query = str(product_name).strip()
    if not query:
        return []

    names = df[product_col].astype("string")
    mask = names.str.contains(re.escape(query), case=False, na=False)
    return _records(df.loc[mask])


def search_product_fuzzy(df, product_name, max_results=50):
    """Fuzzy product search: partial match, case-insensitive, token match."""
    product_col = find_column(df, "product")
    if product_col is None or product_name is None:
        return []

    query = str(product_name).strip().lower()
    if not query:
        return []

    names = df[product_col].astype("string").str.lower()

    mask = names.str.contains(re.escape(query), case=False, na=False)

    if not mask.any():
        tokens = [tok for tok in re.split(r"\s+", query) if len(tok) >= 3]
        if tokens:
            pattern = "|".join(re.escape(tok) for tok in tokens)
            mask = names.str.contains(pattern, case=False, na=False, regex=True)

    return _records(df.loc[mask].head(max_results))


def get_data_preview(df, limit=10):
    """Return the first requested number of rows for a preview."""
    return _records(df.head(max(0, int(limit))))


# ---------------------------------------------------------------------
# ABC Analysis (Pareto classification of products by sales)
# ---------------------------------------------------------------------
def get_abc_analysis(df):
    """
    Classify products into A / B / C tiers using cumulative sales share.
    A = products contributing to the top 80% of total sales
    B = next 15%
    C = last 5%
    """
    product_col = find_column(df, "product")
    sales_col = find_column(df, "sales")
    price_col = find_column(df, "price")

    if product_col is None or sales_col is None:
        return {
            "available": False,
            "message": "Product name and sales columns are required for ABC analysis.",
            "a": [], "b": [], "c": [],
            "summary": {},
        }

    working = df.copy()
    working[sales_col] = parse_numeric_series(working[sales_col])
    working = working.dropna(subset=[product_col, sales_col])

    if working.empty:
        return {
            "available": False,
            "message": "No valid product-sales rows found.",
            "a": [], "b": [], "c": [],
            "summary": {},
        }

    # Aggregate by product
    grouped = (
        working.groupby(product_col, dropna=True)[sales_col]
        .sum()
        .reset_index()
        .rename(columns={product_col: "product", sales_col: "sales"})
    )

    # Optional revenue column
    if price_col:
        working[price_col] = parse_numeric_series(working[price_col])
        revenue = (
            working.assign(_revenue=working[sales_col] * working[price_col])
            .groupby(product_col, dropna=True)["_revenue"]
            .sum()
            .reset_index()
            .rename(columns={product_col: "product", "_revenue": "revenue"})
        )
        grouped = grouped.merge(revenue, on="product", how="left")
    else:
        grouped["revenue"] = None

    grouped = grouped.sort_values("sales", ascending=False).reset_index(drop=True)

    total_sales = float(grouped["sales"].sum())
    if total_sales <= 0:
        return {
            "available": False,
            "message": "Total sales is zero — ABC classification is not meaningful.",
            "a": [], "b": [], "c": [],
            "summary": {},
        }

    grouped["cumulative_sales"] = grouped["sales"].cumsum()
    grouped["cumulative_pct"] = grouped["cumulative_sales"] / total_sales * 100

    def classify(pct):
        if pct <= 80:
            return "A"
        if pct <= 95:
            return "B"
        return "C"

    grouped["abc_tier"] = grouped["cumulative_pct"].apply(classify)

    def tier_records(subset):
        return _records(subset[["product", "sales", "revenue", "cumulative_pct"]])

    a_rows = grouped[grouped["abc_tier"] == "A"]
    b_rows = grouped[grouped["abc_tier"] == "B"]
    c_rows = grouped[grouped["abc_tier"] == "C"]

    return {
        "available": True,
        "a": tier_records(a_rows),
        "b": tier_records(b_rows),
        "c": tier_records(c_rows),
        "summary": {
            "total_products": int(len(grouped)),
            "total_sales": round(total_sales, 2),
            "a_count": int(len(a_rows)),
            "b_count": int(len(b_rows)),
            "c_count": int(len(c_rows)),
            "a_sales_pct": round(float(a_rows["sales"].sum() / total_sales * 100), 2),
            "b_sales_pct": round(float(b_rows["sales"].sum() / total_sales * 100), 2),
            "c_sales_pct": round(float(c_rows["sales"].sum() / total_sales * 100), 2),
        },
    }


# ---------------------------------------------------------------------
# Dead Stock Detection
# ---------------------------------------------------------------------
def get_dead_stock(df, sales_threshold=0):
    """
    Find products that hold stock but have sales <= threshold (default 0).
    Returns:
        - records: list of dead-stock products with value at risk
        - summary: totals
    """
    product_col = find_column(df, "product")
    stock_col = find_column(df, "stock")
    sales_col = find_column(df, "sales")
    price_col = find_column(df, "price")

    if product_col is None or stock_col is None or sales_col is None:
        return {
            "available": False,
            "message": "Product, stock and sales columns are required.",
            "records": [],
            "summary": {},
        }

    working = df.copy()
    working["_stock"] = parse_numeric_series(working[stock_col])
    working["_sales"] = parse_numeric_series(working[sales_col])
    if price_col:
        working["_price"] = parse_numeric_series(working[price_col])
    else:
        working["_price"] = np.nan

    working = working.dropna(subset=[product_col, "_stock", "_sales"])

    if working.empty:
        return {
            "available": False,
            "message": "No valid stock/sales records.",
            "records": [],
            "summary": {},
        }

    # Aggregate per product
    grouped = (
        working.groupby(product_col, dropna=True)
        .agg(
            total_stock=("_stock", "sum"),
            total_sales=("_sales", "sum"),
            avg_price=("_price", "mean"),
        )
        .reset_index()
        .rename(columns={product_col: "product"})
    )

    dead = grouped[
        (grouped["total_stock"] > 0)
        & (grouped["total_sales"] <= sales_threshold)
    ].copy()

    dead["value_at_risk"] = dead["total_stock"] * dead["avg_price"].fillna(0)

    dead = dead.sort_values("value_at_risk", ascending=False).reset_index(drop=True)

    total_value_at_risk = float(dead["value_at_risk"].sum())
    total_dead_stock_units = float(dead["total_stock"].sum())

    records = _records(
        dead[["product", "total_stock", "total_sales", "avg_price", "value_at_risk"]]
        .head(100)
    )

    return {
        "available": True,
        "records": records,
        "summary": {
            "dead_stock_count": int(len(dead)),
            "total_dead_units": round(total_dead_stock_units, 2),
            "total_value_at_risk": round(total_value_at_risk, 2),
            "sales_threshold": sales_threshold,
            "has_price_data": bool(price_col),
        },
    }


# ---------------------------------------------------------------------
# Category × Month Heatmap
# ---------------------------------------------------------------------
def get_category_month_heatmap(df, date_key="received"):
    """
    Build a grid of total sales per category per month.
    Uses Date_Received (or Last_Order_Date if received is missing).
    """
    category_col = find_column(df, "category")
    sales_col = find_column(df, "sales")
    date_col = find_column(df, date_key) or find_column(df, "last_order")

    if category_col is None or sales_col is None or date_col is None:
        return {
            "available": False,
            "message": "Category, sales and a date column are required.",
            "categories": [],
            "months": [],
            "grid": [],
            "max_value": 0,
        }

    working = df[[category_col, sales_col, date_col]].copy()
    working[sales_col] = parse_numeric_series(working[sales_col])
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[category_col, sales_col, date_col])

    if working.empty:
        return {
            "available": False,
            "message": "No valid category-sales-date rows.",
            "categories": [],
            "months": [],
            "grid": [],
            "max_value": 0,
        }

    working["_month"] = working[date_col].dt.strftime("%Y-%m")

    pivot = (
        working.groupby([category_col, "_month"])[sales_col]
        .sum()
        .reset_index()
    )

    categories = sorted(pivot[category_col].astype(str).unique().tolist())
    months = sorted(pivot["_month"].unique().tolist())

    # Build lookup { (category, month) -> value }
    lookup = {}
    for _, row in pivot.iterrows():
        cat = str(row[category_col])
        m = row["_month"]
        val = float(row[sales_col])
        lookup[(cat, m)] = val

    grid = []
    max_value = 0.0
    for cat in categories:
        row_values = []
        for m in months:
            v = lookup.get((cat, m), 0.0)
            row_values.append(round(v, 2))
            if v > max_value:
                max_value = v
        grid.append({"category": cat, "values": row_values})

    return {
        "available": True,
        "categories": categories,
        "months": months,
        "grid": grid,
        "max_value": round(max_value, 2),
    }


# ---------------------------------------------------------------------
# Reorder Point Calculator
# ---------------------------------------------------------------------
def get_reorder_points(df, lead_time_days=7):
    """
    Compute a smart reorder point per product using sales velocity.
    Reorder Point = (daily_sales × lead_time_days) + safety_stock
    Suggested order = max(0, reorder_point × 2 − current_stock)
    """
    product_col = find_column(df, "product")
    stock_col = find_column(df, "stock")
    sales_col = find_column(df, "sales")
    reorder_level_col = find_column(df, "reorder_level")
    price_col = find_column(df, "price")
    date_col = find_column(df, "received") or find_column(df, "last_order")

    if product_col is None or stock_col is None or sales_col is None:
        return {
            "available": False,
            "message": "Product, stock and sales columns are required.",
            "records": [],
            "summary": {},
        }

    working = df.copy()
    working["_stock"] = parse_numeric_series(working[stock_col])
    working["_sales"] = parse_numeric_series(working[sales_col])
    if reorder_level_col:
        working["_reorder_level"] = parse_numeric_series(working[reorder_level_col])
    else:
        working["_reorder_level"] = np.nan
    if price_col:
        working["_price"] = parse_numeric_series(working[price_col])
    else:
        working["_price"] = np.nan

    # Estimate days in dataset
    dataset_days = 30
    if date_col:
        dates = pd.to_datetime(working[date_col], errors="coerce").dropna()
        if not dates.empty:
            dataset_days = max(1, int((dates.max() - dates.min()).days) or 30)

    working = working.dropna(subset=[product_col, "_stock", "_sales"])
    if working.empty:
        return {
            "available": False,
            "message": "No valid stock/sales records.",
            "records": [],
            "summary": {},
        }

    grouped = (
        working.groupby(product_col, dropna=True)
        .agg(
            current_stock=("_stock", "sum"),
            total_sales=("_sales", "sum"),
            recorded_reorder_level=("_reorder_level", "mean"),
            avg_price=("_price", "mean"),
        )
        .reset_index()
        .rename(columns={product_col: "product"})
        )

    records = []
    for _, row in grouped.iterrows():
        daily_sales = float(row["total_sales"]) / dataset_days
        safety_stock = daily_sales * 2
        reorder_point = daily_sales * lead_time_days + safety_stock

        recorded = row["recorded_reorder_level"]
        if pd.notna(recorded) and recorded > 0:
            reorder_point = max(reorder_point, float(recorded))

        current_stock = float(row["current_stock"])
        suggested = max(0.0, reorder_point * 2 - current_stock)

        if current_stock <= reorder_point:
            status = "Critical"
        elif current_stock <= reorder_point * 1.25:
            status = "Watch"
        else:
            status = "Healthy"

        records.append({
            "product": str(row["product"]),
            "current_stock": round(current_stock, 2),
            "daily_sales": round(daily_sales, 2),
            "reorder_point": round(reorder_point, 2),
            "suggested_order": round(suggested, 2),
            "status": status,
            "avg_price": round(float(row["avg_price"]), 2) if pd.notna(row["avg_price"]) else None,
        })

    records.sort(key=lambda r: (r["status"] != "Critical", r["status"] != "Watch", -r["suggested_order"]))

    critical = sum(1 for r in records if r["status"] == "Critical")
    watch = sum(1 for r in records if r["status"] == "Watch")
    healthy = sum(1 for r in records if r["status"] == "Healthy")
    total_order_units = sum(r["suggested_order"] for r in records if r["status"] in ("Critical", "Watch"))

    return {
        "available": True,
        "lead_time_days": lead_time_days,
        "dataset_days": dataset_days,
        "records": records[:200],
        "summary": {
            "total_products": len(records),
            "critical": critical,
            "watch": watch,
            "healthy": healthy,
            "total_order_units": round(total_order_units, 2),
        },
    }
    

# ---------------------------------------------------------------------
# Supplier Scorecard
# ---------------------------------------------------------------------
def get_supplier_scorecard(df):
    """
    Score each supplier (0-100) based on inventory health and contribution.
    """
    supplier_col = find_column(df, "supplier")
    product_col = find_column(df, "product")
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder_level")
    sales_col = find_column(df, "sales")
    price_col = find_column(df, "price")

    if supplier_col is None:
        return {
            "available": False,
            "message": "Supplier column is required.",
            "suppliers": [],
            "summary": {},
        }

    working = df.copy()
    working["_stock"] = parse_numeric_series(working[stock_col]) if stock_col else np.nan
    working["_sales"] = parse_numeric_series(working[sales_col]) if sales_col else np.nan
    working["_price"] = parse_numeric_series(working[price_col]) if price_col else np.nan
    working["_reorder"] = parse_numeric_series(working[reorder_col]) if reorder_col else np.nan

    # Determine low stock and dead stock per row
    if stock_col and reorder_col:
        working["_low"] = working["_stock"] <= working["_reorder"]
    else:
        working["_low"] = False
    if stock_col and sales_col:
        working["_dead"] = (working["_stock"] > 0) & (working["_sales"] <= 0)
    else:
        working["_dead"] = False

    # Inventory value per row
    if stock_col and price_col:
        working["_value"] = working["_stock"] * working["_price"]
    else:
        working["_value"] = 0.0

    grouped = working.groupby(supplier_col, dropna=False).agg(
        product_count=(supplier_col, "size"),
        total_stock=("_stock", "sum"),
        total_sales=("_sales", "sum"),
        total_value=("_value", "sum"),
        low_count=("_low", "sum"),
        dead_count=("_dead", "sum"),
    ).reset_index().rename(columns={supplier_col: "supplier"})

    # Global totals for scoring normalisation
    max_value = max(float(grouped["total_value"].max()), 1.0)
    max_stock = max(float(grouped["total_stock"].max()), 1.0)
    max_products = max(int(grouped["product_count"].max()), 1)

    suppliers = []
    for _, row in grouped.iterrows():
        product_count = int(row["product_count"])
        total_stock = float(row["total_stock"]) if pd.notna(row["total_stock"]) else 0.0
        total_value = float(row["total_value"]) if pd.notna(row["total_value"]) else 0.0
        low_count = int(row["low_count"])
        dead_count = int(row["dead_count"])

        # Contribution sub-score (0-50)
        value_score = (total_value / max_value) * 25
        stock_score = (total_stock / max_stock) * 15
        product_score = (product_count / max_products) * 10
        contribution = value_score + stock_score + product_score

        # Risk penalty (0-50)
        low_ratio = low_count / product_count if product_count > 0 else 0.0
        dead_ratio = dead_count / product_count if product_count > 0 else 0.0
        penalty = (low_ratio * 30) + (dead_ratio * 20)

        score = max(0.0, min(100.0, contribution + (50 - penalty)))

        if score >= 70:
            grade = "A"
        elif score >= 50:
            grade = "B"
        elif score >= 30:
            grade = "C"
        else:
            grade = "D"

        suppliers.append({
            "supplier": str(row["supplier"]),
            "product_count": product_count,
            "total_stock": round(total_stock, 2),
            "total_value": round(total_value, 2),
            "low_stock_count": low_count,
            "dead_stock_count": dead_count,
            "score": round(score, 1),
            "grade": grade,
        })

    suppliers.sort(key=lambda s: s["score"], reverse=True)

    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in suppliers:
        grade_counts[s["grade"]] += 1

    return {
        "available": True,
        "suppliers": suppliers,
        "summary": {
            "total_suppliers": len(suppliers),
            "grade_a": grade_counts["A"],
            "grade_b": grade_counts["B"],
            "grade_c": grade_counts["C"],
            "grade_d": grade_counts["D"],
        },
    }
    

# ---------------------------------------------------------------------
# FEATURE 6 — WHAT-IF SIMULATOR
# ---------------------------------------------------------------------
def get_what_if_simulator(df, price_change_pct=0.0, sales_change_pct=0.0):
    sales_col = find_column(df, "sales")
    price_col = find_column(df, "price")
    if sales_col is None or price_col is None:
        return {"available": False, "message": "Sales and price columns are required."}

    working = df.copy()
    working["_sales"] = parse_numeric_series(working[sales_col])
    working["_price"] = parse_numeric_series(working[price_col])
    working = working.dropna(subset=["_sales", "_price"])

    if working.empty:
        return {"available": False, "message": "No valid sales/price records."}

    current_revenue = float((working["_sales"] * working["_price"]).sum())
    current_units = float(working["_sales"].sum())

    new_price = working["_price"] * (1 + price_change_pct / 100)
    new_sales = working["_sales"] * (1 + sales_change_pct / 100)
    projected_revenue = float((new_sales * new_price).sum())
    projected_units = float(new_sales.sum())

    delta_revenue = projected_revenue - current_revenue
    delta_pct = (delta_revenue / current_revenue * 100) if current_revenue > 0 else 0.0

    return {
        "available": True,
        "price_change_pct": price_change_pct,
        "sales_change_pct": sales_change_pct,
        "current": {"revenue": round(current_revenue, 2), "units": round(current_units, 2)},
        "projected": {"revenue": round(projected_revenue, 2), "units": round(projected_units, 2)},
        "delta": {"revenue": round(delta_revenue, 2), "percent": round(delta_pct, 2)},
    }


# ---------------------------------------------------------------------
# FEATURE 7 — AI COPILOT WITH MEMORY
# ---------------------------------------------------------------------
def ask_dataset_question_with_memory(df, question, history=None):
    history = history or []
    q_lower = str(question).strip().lower()

    # Follow-up context resolution (e.g. "those", "them", "same")
    if any(word in q_lower for word in ["those", "them", "same", "these"]):
        if history:
            last_products = history[-1].get("products", [])
            if last_products:
                return {
                    "success": True,
                    "answer": f"Here are the {len(last_products)} products from the previous question.",
                    "records": last_products,
                    "products": last_products,
                }

    # Fallback to base ask
    from ml_engine import ask_dataset_question
    result = ask_dataset_question(df, question)
    
    # Store product names for follow-up
    if result.get("records"):
        result["products"] = [
            r.get("Product_Name") or r.get("product") or "Unknown" 
            for r in result["records"][:20]
        ]
    return result


# ---------------------------------------------------------------------
# FEATURE 9 — BUSINESS RISK MAP
# ---------------------------------------------------------------------
def get_business_risk_map(df):
    cat_col = find_column(df, "category")
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder_level")
    sales_col = find_column(df, "sales")
    expiry_col = find_column(df, "expiry")

    if cat_col is None or stock_col is None or reorder_col is None:
        return {"available": False, "message": "Category, stock, and reorder columns are required."}

    working = df.copy()
    working["_stock"] = parse_numeric_series(working[stock_col])
    working["_reorder"] = parse_numeric_series(working[reorder_col])
    working["_sales"] = parse_numeric_series(working[sales_col]) if sales_col else np.nan

    risk_counts = {}
    for _, row in working.iterrows():
        cat = str(row[cat_col])
        stock = float(row["_stock"])
        reorder = float(row["_reorder"])
        
        if cat not in risk_counts:
            risk_counts[cat] = {"low_stock": 0, "dead_stock": 0, "expiring": 0}

        if stock <= reorder:
            risk_counts[cat]["low_stock"] += 1
        if sales_col and stock > 0 and row["_sales"] <= 0:
            risk_counts[cat]["dead_stock"] += 1
        if expiry_col and pd.notna(row[expiry_col]):
            try:
                exp_date = pd.to_datetime(row[expiry_col])
                if (exp_date - pd.Timestamp.now()).days <= 30:
                    risk_counts[cat]["expiring"] += 1
            except:
                pass

    risk_map = []
    for cat, counts in risk_counts.items():
        total = sum(counts.values())
        score = min(100, total * 10)
        risk_map.append({
            "category": cat,
            "low_stock": counts["low_stock"],
            "dead_stock": counts["dead_stock"],
            "expiring": counts["expiring"],
            "risk_score": score,
        })

    risk_map.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "available": True,
        "risk_map": risk_map,
        "total_risk_categories": len([r for r in risk_map if r["risk_score"] > 0]),
    }