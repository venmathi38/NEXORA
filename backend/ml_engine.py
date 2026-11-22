import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# --------------------------------------------------
# COLUMN DETECTION
# --------------------------------------------------

COLUMN_ALIASES = {
    "product": ["product_name", "product", "item_name"],
    "stock": ["stock_quantity", "stock", "quantity"],
    "reorder": ["reorder_level", "reorder_point"],
    "reorder_qty": ["reorder_quantity", "suggested_reorder_quantity"],
    "sales": ["sales_volume", "sales", "quantity_sold"],
    "price": ["unit_price", "price", "selling_price"],
    "turnover": ["inventory_turnover_rate", "turnover_rate"],
    "category": ["category", "catagory", "product_category"],
    "supplier": ["supplier_name", "supplier", "vendor"],
    "date": ["date_received", "date", "order_date", "last_order_date"],
    "expiry": ["expiration_date", "expiry_date", "expiry"],
}


def normalize_column(name):
    return "".join(char.lower() for char in str(name) if char.isalnum())


def find_column(df, key):
    if df is None or not hasattr(df, "columns"):
        return None

    aliases = COLUMN_ALIASES.get(key, [])
    available = {
        normalize_column(column): column
        for column in df.columns
    }

    for alias in aliases:
        normalized = normalize_column(alias)
        if normalized in available:
            return available[normalized]

    return None


def numeric_data(df, column):
    values = df[column].astype("string").str.strip()
    values = values.str.replace(r"[,$€£₹\s]", "", regex=True)
    negative = values.str.match(r"^\(.*\)$", na=False)
    values = values.str.replace(r"[()]", "", regex=True)
    parsed = pd.to_numeric(values, errors="coerce")
    return parsed.where(~negative, -parsed.abs())


def safe_records(df):
    """Convert records to JSON-friendly values, including NaN and infinity."""
    if df is None or df.empty:
        return []

    safe = df.replace([np.inf, -np.inf], np.nan).astype(object)
    safe = safe.where(pd.notna(safe), None)
    return safe.to_dict(orient="records")


# --------------------------------------------------
# 1. INVENTORY RISK INTELLIGENCE
# --------------------------------------------------

def inventory_risk_analysis(df):
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder")
    product_col = find_column(df, "product")

    if stock_col is None or reorder_col is None:
        return {
            "available": False,
            "message": "Stock and reorder columns are required.",
        }

    result = df.copy()
    result["_stock"] = numeric_data(result, stock_col)
    result["_reorder"] = numeric_data(result, reorder_col)
    result = result.dropna(subset=["_stock", "_reorder"])

    if result.empty:
        return {
            "available": False,
            "message": "No valid inventory records found.",
        }

    def assess(row):
        stock = row["_stock"]
        reorder = row["_reorder"]

        if stock < 0 or reorder < 0:
            return "Invalid", "Invalid stock or reorder value"
        if stock == 0:
            return "Critical", "Stockout"
        if stock <= reorder:
            return "Critical", "Below reorder level"
        if reorder > 0 and stock <= reorder * 1.25:
            return "High", "Stock is approaching reorder level"
        if reorder > 0 and stock > reorder * 4:
            return "Moderate", "Possible overstock"
        return "Low", "Stock within monitored range"

    assessments = result.apply(assess, axis=1)
    result["Risk_Level"] = assessments.apply(lambda item: item[0])
    result["Risk_Reason"] = assessments.apply(lambda item: item[1])

    if product_col:
        result["Product"] = result[product_col].astype(str)

    records = result[
        [
            column for column in [
                "Product",
                "_stock",
                "_reorder",
                "Risk_Level",
                "Risk_Reason",
            ]
            if column in result.columns
        ]
    ].rename(columns={
        "_stock": "Current_Stock",
        "_reorder": "Reorder_Level",
    })

    counts = result["Risk_Level"].value_counts()

    return {
        "available": True,
        "total_analysed": int(len(result)),
        "critical": int(counts.get("Critical", 0)),
        "high": int(counts.get("High", 0)),
        "moderate": int(counts.get("Moderate", 0)),
        "low": int(counts.get("Low", 0)),
        "invalid": int(counts.get("Invalid", 0)),
        "records": safe_records(records),
    }


# --------------------------------------------------
# 2. MACHINE LEARNING ANOMALY DETECTION
# --------------------------------------------------

def detect_anomalies(df):
    feature_keys = ["stock", "reorder", "sales", "price", "turnover"]
    selected_columns = []

    for key in feature_keys:
        column = find_column(df, key)
        if column is not None and column not in selected_columns:
            selected_columns.append(column)

    if not selected_columns:
        return {
            "available": False,
            "message": "No supported numeric business features found.",
        }

    numeric_df = df[selected_columns].copy()

    for column in selected_columns:
        numeric_df[column] = numeric_data(numeric_df, column)

    numeric_df = numeric_df.replace([np.inf, -np.inf], np.nan)
    numeric_df = numeric_df.dropna(axis=1, how="all")
    numeric_df = numeric_df.dropna(how="all")

    if len(numeric_df) < 20:
        return {
            "available": False,
            "message": "At least 20 usable records are required.",
        }

    numeric_df = numeric_df.fillna(numeric_df.median())
    numeric_df = numeric_df.loc[:, numeric_df.nunique() > 1]

    if numeric_df.shape[1] == 0:
        return {
            "available": False,
            "message": "No varying numeric features found.",
        }

    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(numeric_df)

    model = IsolationForest(
        n_estimators=150,
        contamination="auto",
        random_state=42,
    )

    predictions = model.fit_predict(scaled_data)
    scores = model.decision_function(scaled_data)

    output = df.loc[numeric_df.index].copy()
    output["Anomaly_Status"] = [
        "Anomaly" if value == -1 else "Normal"
        for value in predictions
    ]
    output["Anomaly_Score"] = scores.round(4)

    anomalies = output[output["Anomaly_Status"] == "Anomaly"]

    return {
        "available": True,
        "algorithm": "Isolation Forest",
        "records_analysed": int(len(output)),
        "features_used": list(numeric_df.columns),
        "anomaly_count": int(len(anomalies)),
        "normal_count": int(len(output) - len(anomalies)),
        "records": safe_records(anomalies.head(100)),
    }


# --------------------------------------------------
# 3. SMART REORDER RECOMMENDATIONS
# --------------------------------------------------

def reorder_recommendations(df):
    product_col = find_column(df, "product")
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder")
    reorder_qty_col = find_column(df, "reorder_qty")

    if stock_col is None or reorder_col is None:
        return {
            "available": False,
            "message": "Stock and reorder columns are required.",
        }

    result = df.copy()
    result["_stock"] = numeric_data(result, stock_col)
    result["_reorder"] = numeric_data(result, reorder_col)

    if reorder_qty_col:
        result["_recorded_qty"] = numeric_data(result, reorder_qty_col)
    else:
        result["_recorded_qty"] = np.nan

    result = result.dropna(subset=["_stock", "_reorder"])
    recommendations = []

    for _, row in result.iterrows():
        stock = row["_stock"]
        reorder = row["_reorder"]

        if stock < 0 or reorder < 0 or stock > reorder:
            continue

        recorded_qty = row["_recorded_qty"]

        if pd.notna(recorded_qty) and recorded_qty > 0:
            suggested = int(np.ceil(recorded_qty))
            method = "Based on recorded reorder quantity"
        else:
            suggested = int(np.ceil(max(0, reorder * 2 - stock)))
            method = "Estimated to reach twice the reorder level"

        recommendations.append({
            "product": (
                str(row[product_col])
                if product_col and pd.notna(row[product_col])
                else "Unknown product"
            ),
            "current_stock": float(stock),
            "reorder_level": float(reorder),
            "suggested_quantity": suggested,
            "calculation_method": method,
            "reason": "Stock is at or below the recorded reorder level.",
        })

    return {
        "available": True,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
    }


# --------------------------------------------------
# 4. PRODUCT PERFORMANCE INTELLIGENCE
# --------------------------------------------------

def product_performance(df):
    product_col = find_column(df, "product")
    sales_col = find_column(df, "sales")
    stock_col = find_column(df, "stock")

    if product_col is None or sales_col is None:
        return {
            "available": False,
            "message": "Product name and sales columns are required.",
        }

    result = df.copy()
    result["_sales"] = numeric_data(result, sales_col)

    if stock_col:
        result["_stock"] = numeric_data(result, stock_col)

    result = result.dropna(subset=["_sales", product_col])

    if result.empty:
        return {
            "available": False,
            "message": "No valid product sales records found.",
        }

    aggregations = {"_sales": "sum"}
    if stock_col:
        aggregations["_stock"] = "mean"

    grouped = (
        result.groupby(product_col, dropna=True)
        .agg(aggregations)
        .reset_index()
        .sort_values("_sales", ascending=False)
    )

    def format_product(row):
        item = {
            "product": str(row[product_col]),
            "sales_volume": float(row["_sales"]),
        }
        if stock_col and pd.notna(row["_stock"]):
            item["average_stock"] = float(row["_stock"])
        return item

    return {
        "available": True,
        "products_analysed": int(len(grouped)),
        "top_products": [
            format_product(row)
            for _, row in grouped.head(20).iterrows()
        ],
        "bottom_products": [
            format_product(row)
            for _, row in grouped.tail(10).sort_values("_sales").iterrows()
        ],
    }
# --------------------------------------------------
# 5. DATASET QUESTION ENGINE (rule-based Copilot)
# --------------------------------------------------

def ask_dataset_question(df, question):
    def response(success, answer, insights=None, records=None, chart=None):
        return {
            "success": success,
            "answer": answer,
            "insights": insights or [],
            "records": records or [],
            "chart": chart,
        }

    if df is None or df.empty:
        return response(False, "Please upload a dataset first.")

    question = str(question).strip().lower()
    if not question:
        return response(False, "Please enter a question.")

    product_col = find_column(df, "product")
    stock_col = find_column(df, "stock")
    reorder_col = find_column(df, "reorder")
    sales_col = find_column(df, "sales")
    category_col = find_column(df, "category")
    supplier_col = find_column(df, "supplier")

    if any(word in question for word in ["low stock", "reorder", "out of stock", "stockout"]):
        if stock_col is None or reorder_col is None:
            return response(False, "Stock and reorder columns are missing.")
        stock, reorder = numeric_data(df, stock_col), numeric_data(df, reorder_col)
        matches = df.loc[stock.notna() & reorder.notna() & (stock <= reorder)].copy()
        matches["Current_Stock"] = stock.loc[matches.index]
        matches["Reorder_Level"] = reorder.loc[matches.index]
        return response(
            True,
            f"{len(matches)} records are at or below their reorder level.",
            [{"label": "Low stock records", "value": int(len(matches))}],
            safe_records(matches),
        )

    if "sales" in question:
        if sales_col is None:
            return response(False, "Sales information is unavailable.")
        sales = numeric_data(df, sales_col)
        total = float(sales.sum())
        return response(
            True,
            f"Total recorded sales volume is {total:,.2f}.",
            [{"label": "Sales volume", "value": total}],
        )

    if "stock" in question:
        if stock_col is None:
            return response(False, "Stock information is unavailable.")
        total = float(numeric_data(df, stock_col).sum())
        return response(
            True,
            f"Total recorded stock quantity is {total:,.2f}.",
            [{"label": "Stock units", "value": total}],
        )

    if "category" in question:
        if category_col is None:
            return response(False, "Category information is unavailable.")
        counts = df[category_col].value_counts(dropna=True)
        if counts.empty:
            return response(False, "No category values were found.")
        chart_data = [
            {"label": str(label), "value": int(value)}
            for label, value in counts.items()
        ]
        return response(
            True,
            f"The category with the most records is {counts.index[0]} ({int(counts.iloc[0])} records).",
            [{"label": "Categories", "value": int(len(counts))}],
            chart={"type": "bar", "title": "Records by category", "data": chart_data},
        )

    if "supplier" in question:
        if supplier_col is None:
            return response(False, "Supplier information is unavailable.")
        count = int(df[supplier_col].nunique(dropna=True))
        return response(
            True,
            f"The dataset contains {count} unique suppliers.",
            [{"label": "Suppliers", "value": count}],
        )

    if product_col and any(word in question for word in ["product", "show", "find", "search"]):
        search_terms = question
        for word in [
            "show me", "show", "find", "search for", "search",
            "details of", "details", "product",
        ]:
            search_terms = search_terms.replace(word, " ")
        search_terms = " ".join(search_terms.split())
        if not search_terms:
            return response(False, "Please include a product name in your question.")
        matches = df[
            df[product_col]
            .astype(str)
            .str.contains(search_terms, case=False, na=False, regex=False)
        ]
        if matches.empty:
            return response(True, f"No product matching '{search_terms}' was found.")
        records = safe_records(matches.head(100))
        return response(
            True,
            f"Found {len(matches)} matching product records.",
            [{"label": "Matching records", "value": int(len(matches))}],
            records,
        )

    return response(
        False,
        "I can currently analyse sales, stock, low stock, reorder levels, "
        "products, categories and suppliers.",
    )


# --------------------------------------------------
# 6. SALES FORECAST (simple, honest, evaluated)
# --------------------------------------------------

def sales_forecast(df, periods=7):
    """
    Very small trend forecast using a linear fit on daily sales.
    Returns model metrics (MAE / RMSE / R^2) so the UI can show real quality.
    """
    sales_col = find_column(df, "sales")
    date_col = find_column(df, "date")
    if sales_col is None or date_col is None:
        return {
            "available": False,
            "message": "Sales and date columns are required for forecasting.",
        }

    working = df[[date_col, sales_col]].copy()
    working[sales_col] = numeric_data(working, sales_col)
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna()

    if len(working) < 10:
        return {
            "available": False,
            "message": "At least 10 dated sales records are required.",
        }

    daily = (
        working.groupby(date_col)[sales_col].sum()
        .sort_index()
    )

    x = np.arange(len(daily), dtype=float)
    y = daily.to_numpy(dtype=float)

    a, b = np.polyfit(x, y, 1)
    fitted = a * x + b

    residuals = y - fitted
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    ss_res = float(np.sum(residuals ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    future_x = np.arange(len(daily), len(daily) + int(periods), dtype=float)
    forecast_values = a * future_x + b
    future_dates = pd.date_range(
        daily.index[-1] + pd.Timedelta(days=1),
        periods=int(periods),
        freq="D",
    )

    return {
        "available": True,
        "model": "Linear trend",
        "history": [
            {"date": d.isoformat(), "value": float(v)}
            for d, v in daily.items()
        ],
        "forecast": [
            {"date": d.isoformat(), "value": float(max(0.0, v))}
            for d, v in zip(future_dates, forecast_values)
        ],
        "metrics": {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4),
        },
    }


def get_ml_metrics(df):
    """Expose the ML evaluation metrics used by the dashboard."""
    return {
        "sales_forecast": sales_forecast(df),
    }


# --------------------------------------------------
# 7. COMBINED AI REPORT
# --------------------------------------------------

def generate_ai_report(df):
    return {
        "inventory_risk": inventory_risk_analysis(df),
        "anomaly_detection": detect_anomalies(df),
        "reorder_recommendations": reorder_recommendations(df),
        "product_performance": product_performance(df),
        "sales_forecast": sales_forecast(df),
    }
    

# =====================================================================
# AI COPILOT V2 — Question bank + natural language + memory
# =====================================================================
import question_bank


def _format_number(value):
    """Helper: format a number with thousands separators."""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def _build_answer_for_intent(df, intent, question, history):
    """Return (answer_text, insights, records, chart) for a detected intent."""
    from engine import (
        get_kpis, get_low_stock, get_overstock, get_expiry_alerts,
        get_expiry_analysis, get_top_selling_products, get_low_selling_products,
        get_category_analysis, get_supplier_analysis, get_recommendations,
        get_abc_analysis, get_business_score, search_product_fuzzy,
        find_column, parse_numeric_series,
    )

    empty = ([], [], [])

    # ---------- TOTAL STOCK ----------
    if intent == "total_stock":
        kpis = get_kpis(df) or {}
        total = kpis.get("total_stock", 0)
        return (
            f"You currently have {_format_number(total)} units in stock "
            f"across {kpis.get('total_products', 0)} products.",
            [{"label": "Total stock", "value": total}],
            [], []
        )

    # ---------- TOTAL SALES ----------
    if intent in ("total_sales", "total_revenue"):
        kpis = get_kpis(df) or {}
        total = kpis.get("total_sales", 0)
        rev = kpis.get("estimated_sales_value") or 0
        text = f"Total recorded sales volume is {_format_number(total)} units."
        if rev:
            text += f" Estimated revenue: {_format_number(rev)} (currency unknown)."
        return (
            text,
            [{"label": "Sales volume", "value": total}],
            [], []
        )

    # ---------- LOW STOCK / REORDER ----------
    if intent == "low_stock":
        products = get_low_stock(df) or []
        return (
            f"{len(products)} products are at or below their reorder level. "
            f"The most critical ones should be ordered immediately.",
            [{"label": "Low stock items", "value": len(products)}],
            products[:50], []
        )

    if intent == "out_of_stock":
        products = get_low_stock(df) or []
        zero_stock = [
            p for p in products
            if _safe_number(p.get("Stock_Quantity") or p.get("Stock") or 0) <= 0
        ]
        return (
            f"{len(zero_stock)} products have zero stock right now.",
            [{"label": "Out of stock", "value": len(zero_stock)}],
            zero_stock[:50], []
        )

    # ---------- OVERSTOCK ----------
    if intent == "overstock":
        items = get_overstock(df) or []
        return (
            f"{len(items)} products are currently overstocked "
            f"(stock above 3× reorder level). Consider reducing their order quantities.",
            [{"label": "Overstocked items", "value": len(items)}],
            items[:50], []
        )

    # ---------- DEAD STOCK ----------
    if intent == "dead_stock":
        from engine import get_dead_stock
        result = get_dead_stock(df) or {}
        records = result.get("records", [])
        total_val = result.get("summary", {}).get("total_value_at_risk", 0)
        return (
            f"{len(records)} products have stock but no sales — "
            f"approximately {_format_number(total_val)} is tied up in dead inventory.",
            [{"label": "Dead stock", "value": len(records)}],
            records[:50], []
        )

    # ---------- EXPIRY ----------
    if intent in ("expiry_alerts", "expiry_soon", "expiry_today", "expiry_month"):
        analysis = get_expiry_analysis(df) or {}
        counts = analysis.get("counts", {})
        expired = counts.get("Expired", 0)
        soon7 = counts.get("Expiring within 7 days", 0)
        soon30 = counts.get("Expiring within 30 days", 0)
        alerts = get_expiry_alerts(df) or []
        return (
            f"Expiry status: {expired} expired, {soon7} expiring within 7 days, "
            f"{soon30} expiring within 30 days. Total needing attention: {len(alerts)}.",
            [
                {"label": "Expired", "value": expired},
                {"label": "≤7 days", "value": soon7},
                {"label": "≤30 days", "value": soon30},
            ],
            alerts[:50], []
        )

    if intent == "expired":
        analysis = get_expiry_analysis(df) or {}
        expired_count = analysis.get("counts", {}).get("Expired", 0)
        alerts = [a for a in (get_expiry_alerts(df) or []) if a.get("expiry_status") == "Expired"]
        return (
            f"{expired_count} products have already expired. "
            f"Remove them from sellable inventory immediately.",
            [{"label": "Expired items", "value": expired_count}],
            alerts[:50], []
        )

    # ---------- TOP SELLING ----------
    if intent == "top_selling":
        items = get_top_selling_products(df, limit=10) or []
        if not items:
            return ("No sales data is available.", [], [], [])
        top = items[0]
        name = list(top.values())[0]
        sales_val = list(top.values())[1] if len(top) > 1 else 0
        return (
            f"Your top-selling product is '{name}' with {_format_number(sales_val)} units sold. "
            f"Here are the top 10 products by sales volume.",
            [{"label": "Top product sales", "value": sales_val}],
            items, []
        )

    # ---------- LOW SELLING ----------
    if intent == "low_selling":
        items = get_low_selling_products(df, limit=10) or []
        return (
            f"Here are the {len(items)} lowest-selling products. "
            f"Consider promotion or discontinuation.",
            [{"label": "Low-selling items", "value": len(items)}],
            items, []
        )

    # ---------- CATEGORY ----------
    if intent in ("category_summary", "top_category", "worst_category", "category_count"):
        cats = get_category_analysis(df) or []
        if not cats:
            return ("No category data found.", [], [], [])

        # Each row has category name + total sales (or stock)
        sorted_cats = sorted(
            cats,
            key=lambda x: _safe_number(list(x.values())[1] if len(x) > 1 else 0),
            reverse=True,
        )
        top = sorted_cats[0] if sorted_cats else {}
        top_name = str(list(top.values())[0]) if top else "Unknown"

        chart_data = [
            {"label": str(list(c.values())[0]), "value": _safe_number(list(c.values())[1] if len(c) > 1 else 0)}
            for c in sorted_cats[:8]
        ]

        return (
            f"You have {len(cats)} categories. "
            f"The top performing category is '{top_name}'.",
            [{"label": "Categories", "value": len(cats)}],
            [],
            {"type": "bar", "title": "Category breakdown", "data": chart_data},
        )

    # ---------- SUPPLIER ----------
    if intent in ("supplier_summary", "top_supplier", "supplier_count"):
        sups = get_supplier_analysis(df) or []
        if not sups:
            return ("No supplier data found.", [], [], [])
        top = sups[0] if sups else {}
        top_name = str(list(top.values())[0]) if top else "Unknown"
        return (
            f"You have {len(sups)} suppliers. "
            f"The supplier with the most products is '{top_name}'.",
            [{"label": "Suppliers", "value": len(sups)}],
            sups[:20], []
        )

    # ---------- PRODUCTS ----------
    if intent in ("product_count", "list_products"):
        kpis = get_kpis(df) or {}
        count = kpis.get("total_products", 0)
        return (
            f"You have {count} unique products in your catalogue.",
            [{"label": "Products", "value": count}],
            [], []
        )

    # ---------- INVENTORY VALUE ----------
    if intent == "inventory_value":
        kpis = get_kpis(df) or {}
        val = kpis.get("inventory_value", 0)
        return (
            f"Your total inventory value is {_format_number(val)} "
            f"(currency unknown — dataset does not specify).",
            [{"label": "Inventory value", "value": val}],
            [], []
        )

    # ---------- ABC ----------
    if intent == "abc_analysis":
        abc = get_abc_analysis(df) or {}
        if not abc.get("available"):
            return (abc.get("message", "ABC analysis unavailable."), [], [], [])
        summary = abc.get("summary", {})
        return (
            f"ABC classification: {summary.get('a_count', 0)} products in Tier A "
            f"(top 80% sales), {summary.get('b_count', 0)} in Tier B, "
            f"{summary.get('c_count', 0)} in Tier C.",
            [
                {"label": "Tier A", "value": summary.get("a_count", 0)},
                {"label": "Tier B", "value": summary.get("b_count", 0)},
                {"label": "Tier C", "value": summary.get("c_count", 0)},
            ],
            [], []
        )

    # ---------- BUSINESS SCORE / SUMMARY ----------
    if intent in ("business_score", "business_summary", "business_risk"):
        kpis = get_kpis(df) or {}
        score = get_business_score(df) or {}
        recs = get_recommendations(df) or []
        low = get_low_stock(df) or []
        over = get_overstock(df) or []
        alerts = get_expiry_alerts(df) or []

        text = (
            f"Business health overview: {kpis.get('total_products', 0)} products, "
            f"{_format_number(kpis.get('total_stock', 0))} stock units, "
            f"{_format_number(kpis.get('inventory_value', 0))} inventory value. "
            f"{len(low)} low-stock items, {len(over)} overstocked items, "
            f"{len(alerts)} expiry alerts."
        )
        return (
            text,
            [
                {"label": "Low stock", "value": len(low)},
                {"label": "Overstock", "value": len(over)},
                {"label": "Expiry alerts", "value": len(alerts)},
                {"label": "Business score", "value": score.get("score", 0)},
            ],
            [], []
        )

    # ---------- RECOMMENDATIONS ----------
    if intent == "recommendations":
        recs = get_recommendations(df) or []
        text = "Business recommendations:\n\n• " + "\n• ".join(str(r) for r in recs)
        return (text, [], [], [])

    # ---------- SEARCH PRODUCT ----------
    if intent in ("search_product", "product_details", "compare_products"):
        # Extract product name by removing common verb phrases
        stopwords = [
            "search", "find", "look for", "where is", "details of", "info about",
            "tell me about", "show me", "price of", "cost of", "stock of",
            "supplier of", "who supplies", "compare", "vs", "versus", "and",
            "product", "?", "the",
        ]
        cleaned = question.lower()
        for w in stopwords:
            cleaned = cleaned.replace(w, " ")
        cleaned = " ".join(cleaned.split())
        if not cleaned:
            return (
                "I can look up any product. Try asking: 'tell me about ProductName'.",
                [], [], []
            )

        matches = search_product_fuzzy(df, cleaned, max_results=10) or []
        if not matches:
            return (
                f"No product matched '{cleaned}'. Try a simpler search term.",
                [], [], []
            )
        names = [
            str(m.get("Product_Name") or m.get("product") or "Unknown")
            for m in matches[:5]
        ]
        return (
            f"Found {len(matches)} products matching '{cleaned}'. "
            f"Top matches: {', '.join(names)}.",
            [{"label": "Matches", "value": len(matches)}],
            matches, []
        )

    # ---------- FOLLOW-UP ----------
    if intent == "followup":
        if history:
            last = history[-1] if isinstance(history[-1], dict) else {}
            last_answer = last.get("answer", "the previous answer")
            last_records = last.get("records", [])
            return (
                f"Following up on the previous answer: {last_answer} "
                f"You can see {len(last_records)} records in the previous result.",
                [], last_records[:50], []
            )
        return (
            "There is no prior question to follow up on. Please ask a new question.",
            [], [], []
        )

    # ---------- HELP / GREETING ----------
    if intent == "greeting":
        return (
            "Hello! I am NEXORA AI Copilot. Ask me about stock, sales, expiry, "
            "categories, suppliers, ABC analysis, or business recommendations.",
            [], [], []
        )

    if intent == "help":
        return (
            "I can answer 200+ question variations about:\n"
            "• Stock levels & low-stock alerts\n"
            "• Sales & revenue\n"
            "• Expiry tracking\n"
            "• Categories & suppliers\n"
            "• ABC analysis (Pareto)\n"
            "• Recommendations & business health\n"
            "• Individual products\n\n"
            "Try: 'What should I reorder?', 'Any expiring soon?', 'Top selling products'",
            [], [], []
        )

    # ---------- UNKNOWN ----------
    return (
        "I didn't recognise that question. I understand 200+ phrasings about stock, "
        "sales, expiry, categories, suppliers, recommendations and product lookups. "
        "Try: 'low stock', 'top products', 'expiring soon', or 'tell me about Bread'.",
        [], [], []
    )


def _safe_number(value):
    """Convert any value to a float, default 0."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def ask_dataset_question_v2(df, question, history=None):
    """
    NEXORA AI Copilot — question-bank driven with memory.

    Args:
        df: uploaded DataFrame
        question: user's natural language question
        history: list of {question, answer, records} from previous turns

    Returns:
        dict with success, answer, insights, records, chart, intent, memory_size
    """
    if df is None or df.empty:
        return {
            "success": False,
            "answer": "Please upload a dataset first.",
            "insights": [], "records": [], "chart": None,
            "intent": "unknown", "memory_size": 0,
        }

    history = history or []
    question = str(question).strip()

    if not question:
        return {
            "success": False,
            "answer": "Please type a question.",
            "insights": [], "records": [], "chart": None,
            "intent": "unknown", "memory_size": len(history),
        }

    intent = question_bank.detect_intent(question)
    answer, insights, records, chart = _build_answer_for_intent(df, intent, question, history)

    return {
        "success": True,
        "answer": answer,
        "insights": insights,
        "records": records,
        "chart": chart,
        "intent": intent,
        "memory_size": len(history),
    }