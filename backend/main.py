import importlib
import io
import math
import uuid as _uuid
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

try:
    import engine
    import ml_engine
    import clean_engine as clean_engine_module
except Exception as import_error:
    raise RuntimeError(
        f"NEXORA backend failed to import engine/ml_engine/clean_engine: {import_error}"
    ) from import_error


app = FastAPI(
    title="NEXORA AI",
    description="Smart Retail Intelligence & Decision Support System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_dataset: Optional[pd.DataFrame] = None
active_filename: Optional[str] = None
cleaned_cache = {}


class QuestionRequest(BaseModel):
    question: str


class CleanApplyRequest(BaseModel):
    fix_ids: list[str] = []


def clean_json(value):
    """Recursively convert pandas/NumPy values into JSON-safe Python values."""
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]

    if isinstance(value, pd.DataFrame):
        return clean_json(value.to_dict(orient="records"))

    if isinstance(value, pd.Series):
        return clean_json(value.to_dict())

    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        number = float(value)
        return number if math.isfinite(number) else None

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and missing:
            return None
    except (TypeError, ValueError):
        pass

    return value


def require_dataset():
    if active_dataset is None:
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV or Excel dataset first.",
        )
    return active_dataset


def safe_engine_call(function_name, df):
    """Run an engine function safely so one failure does not break the whole API."""
    function = getattr(engine, function_name, None)
    if not callable(function):
        return []
    try:
        return clean_json(function(df))
    except Exception:
        return []


@app.get("/")
def home():
    return {"message": "Welcome to NEXORA AI", "status": "running"}


@app.get("/api/health")
def health():
    return {"status": "healthy", "dataset_uploaded": active_dataset is not None}


@app.get("/api/ping")
def ping():
    return {"pong": True}


@app.get("/api/dataset")
def dataset_info():
    if active_dataset is None:
        return {
            "uploaded": False,
            "filename": None,
            "rows": 0,
            "columns": [],
        }
    return {
        "uploaded": True,
        "filename": active_filename,
        "rows": int(len(active_dataset)),
        "columns": [str(column) for column in active_dataset.columns],
    }


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global active_dataset, active_filename

    filename = (file.filename or "").strip()
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if extension not in {"csv", "xlsx", "xls"}:
        raise HTTPException(
            status_code=400,
            detail="Only CSV, XLSX and XLS files are supported.",
        )

    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        if extension == "csv":
            try:
                df = pd.read_csv(io.BytesIO(content))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
        else:
            df = pd.read_excel(io.BytesIO(content))

        if df.empty:
            raise HTTPException(
                status_code=400, detail="The uploaded dataset has no rows."
            )

        df.columns = [str(column).strip() for column in df.columns]

        if df.columns.duplicated().any():
            duplicate_names = df.columns[df.columns.duplicated()].tolist()
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate column names found: {duplicate_names}",
            )

        active_dataset = df
        active_filename = filename

        return {
            "success": True,
            "message": "Dataset uploaded successfully.",
            "filename": filename,
            "rows": int(len(df)),
            "columns": [str(column) for column in df.columns],
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the file: {str(error)}",
        )


@app.get("/api/preview")
def preview_dataset():
    df = require_dataset()
    return {
        "columns": [str(column) for column in df.columns],
        "rows": clean_json(df.head(20).to_dict(orient="records")),
        "total_rows": int(len(df)),
    }


@app.get("/api/dashboard")
def dashboard():
    df = require_dataset()
    return {
        "filename": active_filename,
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "kpis": safe_engine_call("get_kpis", df),
        "low_stock": safe_engine_call("get_low_stock", df),
        "overstock": safe_engine_call("get_overstock", df),
        "expiry_alerts": safe_engine_call("get_expiry_alerts", df),
        "expiry_analysis": safe_engine_call("get_expiry_analysis", df),
        "top_selling": safe_engine_call("get_top_selling_products", df),
        "low_selling": safe_engine_call("get_low_selling_products", df),
        "category_analysis": safe_engine_call("get_category_analysis", df),
        "supplier_analysis": safe_engine_call("get_supplier_analysis", df),
        "recommendations": safe_engine_call("get_recommendations", df),
        "quality": safe_engine_call("get_column_quality", df),
        "sales_trend": safe_engine_call("get_sales_trend", df),
        "inventory_trend": safe_engine_call("get_inventory_trend", df),
        "business_score": safe_engine_call("get_business_score", df),
        "preview": clean_json(df.head(10).to_dict(orient="records")),
    }


@app.get("/api/ai/report")
def ai_report():
    df = require_dataset()
    try:
        return clean_json(ml_engine.generate_ai_report(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"AI report error: {str(error)}"
        )


@app.post("/api/ai/ask")
def ask_ai(request: QuestionRequest):
    df = require_dataset()
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Please enter a question.")

    try:
        result = ml_engine.ask_dataset_question(df, question)
        return {"question": question, **clean_json(result)}
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Question processing error: {str(error)}"
        )


@app.post("/api/ask")
def ask_alias(request: QuestionRequest):
    return ask_ai(request)


@app.get("/api/ai/risk")
def inventory_risk():
    df = require_dataset()
    try:
        return clean_json(ml_engine.inventory_risk_analysis(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Inventory risk error: {str(error)}"
        )


@app.get("/api/ai/anomalies")
def anomalies():
    df = require_dataset()
    try:
        return clean_json(ml_engine.detect_anomalies(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Anomaly detection error: {str(error)}"
        )


@app.get("/api/ai/recommendations")
def ai_recommendations():
    df = require_dataset()
    try:
        return clean_json(ml_engine.reorder_recommendations(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Reorder recommendation error: {str(error)}"
        )


@app.get("/api/ai/performance")
def product_performance():
    df = require_dataset()
    try:
        return clean_json(ml_engine.product_performance(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Product performance error: {str(error)}"
        )


@app.get("/api/ai/forecast")
def forecast():
    df = require_dataset()
    try:
        return clean_json(ml_engine.sales_forecast(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Forecast error: {str(error)}"
        )


# =====================================================================
# SMART DATA CLEANING
# =====================================================================


@app.get("/api/clean/analyze")
def clean_analyze():
    """Inspect the loaded dataset without changing it."""
    df = require_dataset()
    try:
        report = clean_engine_module.analyze_dataset(df)
        return clean_json(report)
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Cleaning analysis error: {str(error)}"
        )


@app.post("/api/clean/apply")
def clean_apply(request: CleanApplyRequest):
    """Apply the user-selected fixes to a copy of the dataset."""
    df = require_dataset()
    try:
        result = clean_engine_module.apply_fixes(df, request.fix_ids)
        cleaned_df = result["cleaned"]
        token = str(_uuid.uuid4())
        cleaned_cache[token] = cleaned_df

        preview = clean_engine_module._safe_preview(cleaned_df, 10)
        return clean_json({
            "success": True,
            "token": token,
            "original_rows": result["original_rows"],
            "cleaned_rows": result["cleaned_rows"],
            "applied": result["applied"],
            "preview": preview,
        })
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Cleaning apply error: {str(error)}"
        )


@app.get("/api/clean/download/{token}")
def clean_download(token: str):
    """Return the cleaned CSV for the given token, then discard it."""
    cleaned_df = cleaned_cache.pop(token, None)
    if cleaned_df is None:
        raise HTTPException(
            status_code=404,
            detail="Cleaned dataset not found. Please re-apply the fixes.",
        )

    csv_bytes = clean_engine_module.to_csv_bytes(cleaned_df)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="NEXORA_cleaned_{token[:8]}.csv"',
        },
    )


@app.get("/api/clean/download-excel")
def clean_download_excel():
    """Auto-apply every fixable cleaning rule and return a formatted .xlsx file."""
    df = require_dataset()
    try:
        xlsx_bytes = clean_engine_module.export_cleaned_excel(df, auto_fix=True)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="NEXORA_Cleaned_Dataset.xlsx"',
            },
        )
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Excel export error: {str(error)}"
        )


# =====================================================================
# FEATURE 1 — ABC ANALYSIS
# =====================================================================


@app.get("/api/analytics/abc")
def abc_analysis():
    """Classify products into A/B/C tiers by cumulative sales share."""
    df = require_dataset()
    try:
        return clean_json(engine.get_abc_analysis(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"ABC analysis error: {str(error)}"
        )


# =====================================================================
# FEATURE 2 — DEAD STOCK
# =====================================================================


@app.get("/api/analytics/dead-stock")
def dead_stock():
    df = require_dataset()
    try:
        return clean_json(engine.get_dead_stock(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Dead stock error: {str(error)}"
        )


# =====================================================================
# FEATURE 3 — CATEGORY × MONTH HEATMAP
# =====================================================================


@app.get("/api/analytics/category-heatmap")
def category_heatmap():
    df = require_dataset()
    try:
        return clean_json(engine.get_category_month_heatmap(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Heatmap error: {str(error)}"
        )


# =====================================================================
# FEATURE 4 — REORDER POINT CALCULATOR
# =====================================================================


@app.get("/api/analytics/reorder-points")
def reorder_points():
    df = require_dataset()
    try:
        return clean_json(engine.get_reorder_points(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Reorder points error: {str(error)}"
        )


# =====================================================================
# FEATURE 5 — SUPPLIER SCORECARD
# =====================================================================


@app.get("/api/analytics/supplier-scorecard")
def supplier_scorecard():
    df = require_dataset()
    try:
        return clean_json(engine.get_supplier_scorecard(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Supplier scorecard error: {str(error)}"
        )


# =====================================================================
# FEATURE 6 — WHAT-IF SIMULATOR
# =====================================================================


class WhatIfRequest(BaseModel):
    price_change_pct: float = 0.0
    sales_change_pct: float = 0.0


@app.post("/api/analytics/what-if")
def what_if(request: WhatIfRequest):
    df = require_dataset()
    try:
        return clean_json(engine.get_what_if_simulator(
            df,
            price_change_pct=request.price_change_pct,
            sales_change_pct=request.sales_change_pct,
        ))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"What-if error: {str(error)}"
        )


# =====================================================================
# FEATURE 7 — AI COPILOT WITH MEMORY
# =====================================================================


class AIAskRequest(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/ai/ask-memory")
def ask_ai_memory(request: AIAskRequest):
    df = require_dataset()
    try:
        result = engine.ask_dataset_question_with_memory(
            df, request.question, request.history
        )
        return {"question": request.question, **clean_json(result)}
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Question processing error: {str(error)}"
        )


# =====================================================================
# FEATURE 8 — AI COPILOT V2 (question bank + memory)
# =====================================================================


class AskV2Request(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/ai/ask-v2")
def ask_ai_v2(request: AskV2Request):
    """NEXORA Copilot with 410 question patterns and session memory."""
    df = require_dataset()
    try:
        result = ml_engine.ask_dataset_question_v2(
            df, request.question, request.history
        )
        return clean_json(result)
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Copilot error: {str(error)}"
        )


# =====================================================================
# FEATURE 9 — BUSINESS RISK MAP
# =====================================================================


@app.get("/api/analytics/risk-map")
def risk_map():
    df = require_dataset()
    try:
        return clean_json(engine.get_business_risk_map(df))
    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Risk map error: {str(error)}"
        )


# =====================================================================
# FEATURE 10 — DATA STORYTELLING
# =====================================================================


@app.get("/api/analytics/story")
def get_story():
    df = require_dataset()
    try:
        kpis = engine.get_kpis(df)
        cat_data = engine.get_category_analysis(df)
        top_cat = cat_data[0] if cat_data else None
        low_stock = engine.get_low_stock(df)
        risk_count = len(low_stock)

        story = (
            f"Your business currently manages "
            f"{kpis.get('total_products', 0)} unique products "
            f"with a total inventory value of "
            f"${kpis.get('inventory_value', 0):,.2f}. "
        )

        if top_cat:
            cat_name = str(list(top_cat.values())[0])
            story += f"Your highest-performing category is '{cat_name}'. "

        if risk_count > 0:
            story += (
                f"However, {risk_count} products are currently at or below "
                "their reorder level. Immediate action is recommended to "
                "replenish these items and avoid stockouts."
            )
        else:
            story += (
                "Inventory health looks stable with no critical low-stock "
                "alerts at this moment."
            )

        return {"available": True, "story": story}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# =====================================================================
# FEATURE 11 — CALCULATION ENGINE
# =====================================================================
import calc_library


@app.get("/api/calculations")
def list_calculations():
    """Return all calculation definitions with their formulas."""
    return {
        "available": True,
        "total": len(calc_library.CALCULATIONS),
        "categories": calc_library.get_categories(),
        "calculations": calc_library.get_all_calculations(),
    }


@app.get("/api/calculations/result/{calc_id}")
def calculation_result(calc_id: str):
    df = require_dataset()

    metric = next(
        (c for c in calc_library.CALCULATIONS if c["id"] == calc_id),
        None,
    )
    if metric is None:
        raise HTTPException(
            status_code=404, detail=f"Calculation '{calc_id}' not found."
        )

    try:
        fn_path = metric["python_fn"]
        module_name, fn_name = fn_path.split(".")
        module = importlib.import_module(module_name)
        function = getattr(module, fn_name)
        result = function(df)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Calculation failed: {str(e)}"
        )

    # --- 1. Scalar numbers (Total Stock, Total Products, etc.) ---
    if metric.get("field") and isinstance(result, dict):
        return clean_json({
            "type": "number",
            "value": result.get(metric["field"]),
            "metric": metric,
        })

    # --- 2. Dead Stock (summary + records) ---
    if calc_id == "dead_stock":
        summary = result.get("summary", {})
        return clean_json({
            "type": "summary_records",
            "summary": summary,
            "records": result.get("records", [])[:50],
            "metric": metric,
        })

    # --- 3. Reorder Points (summary + records) ---
    if calc_id == "reorder_critical":
        summary = result.get("summary", {})
        return clean_json({
            "type": "summary_records",
            "summary": summary,
            "records": result.get("records", [])[:50],
            "metric": metric,
        })

    # --- 4. Business Health Score ---
    if calc_id == "business_score":
        return clean_json({
            "type": "summary",
            "summary": {
                "score": result.get("score"),
                **result.get("components", {}),
            },
            "metric": metric,
        })

    # --- 5. ABC Analysis (bar chart) ---
    if "abc" in calc_id:
        return clean_json({
            "type": "chart",
            "chart_data": [
                {"name": "Tier A", "value": len(result.get("a", []))},
                {"name": "Tier B", "value": len(result.get("b", []))},
                {"name": "Tier C", "value": len(result.get("c", []))},
            ],
            "metric": metric,
        })

    # --- 6. Expiry Analysis (summary) ---
    if "expir" in calc_id:
        counts = result.get("counts", {})
        return clean_json({
            "type": "summary",
            "summary": {
                "expired": counts.get("Expired", 0),
                "expiring_7_days": counts.get("Expiring within 7 days", 0),
                "expiring_30_days": counts.get("Expiring within 30 days", 0),
            },
            "metric": metric,
        })

    # --- 7. Sales Forecast (line chart) ---
    if calc_id == "sales_forecast":
        history = result.get("history", [])
        chart_data = [
            {"name": h["date"][:10], "value": h["value"]}
            for h in history
        ]
        return clean_json({
            "type": "chart",
            "chart_data": chart_data,
            "metrics": result.get("metrics", {}),
            "metric": metric,
        })

    # --- 8. Supplier Scorecard (MUST come before generic "list" check) ---
    if calc_id == "supplier_score":
        suppliers = result.get("suppliers", [])
        return clean_json({
            "type": "table",
            "records": suppliers[:50],
            "count": len(suppliers),
            "metric": metric,
        })

    # --- 9. What-If Simulation ---
    if calc_id == "what_if":
        sim_result = engine.get_what_if_simulator(
            df, price_change_pct=10, sales_change_pct=10
        )
        return clean_json({
            "type": "summary",
            "summary": {
                "current_revenue": sim_result.get("current", {}).get("revenue"),
                "projected_revenue": sim_result.get("projected", {}).get("revenue"),
                "revenue_change_percent": sim_result.get("delta", {}).get("percent"),
            },
            "metric": metric,
        })

    # --- 10. Generic list metrics (Top Selling, Supplier Portfolio, etc.) ---
    if metric.get("list"):
        records = (
            result if isinstance(result, list)
            else result.get("records", [])
        )
        return clean_json({
            "type": "table",
            "records": records[:50],
            "count": len(records),
            "metric": metric,
        })

    # --- Fallback ---
    return clean_json({
        "type": "number",
        "value": str(result),
        "metric": metric,
    })