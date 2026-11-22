"""
NEXORA AI — Calculation Library
Defines all 60+ metrics with their formulas and required columns.
Used by /api/calculations to return a metric registry.
"""

CALCULATIONS = [
    # ================= BASIC =================
    {"id": "total_products", "name": "Total Products", "category": "Basic", "formula": "COUNT(DISTINCT Product_Name)", "required": ["Product_Name"], "python_fn": "engine.get_kpis", "field": "total_products"},
    {"id": "total_stock", "name": "Total Stock Units", "category": "Basic", "formula": "SUM(Stock_Quantity)", "required": ["Stock_Quantity"], "python_fn": "engine.get_kpis", "field": "total_stock"},
    {"id": "total_sales", "name": "Total Sales Volume", "category": "Basic", "formula": "SUM(Sales_Volume)", "required": ["Sales_Volume"], "python_fn": "engine.get_kpis", "field": "total_sales"},
    {"id": "inventory_value", "name": "Inventory Value", "category": "Basic", "formula": "SUM(Stock_Quantity × Unit_Price)", "required": ["Stock_Quantity", "Unit_Price"], "python_fn": "engine.get_kpis", "field": "inventory_value"},
    {"id": "est_sales_value", "name": "Estimated Sales Value", "category": "Basic", "formula": "SUM(Sales_Volume × Unit_Price)", "required": ["Sales_Volume", "Unit_Price"], "python_fn": "engine.get_kpis", "field": "estimated_sales_value"},
    {"id": "avg_turnover", "name": "Average Turnover Rate", "category": "Basic", "formula": "AVERAGE(Inventory_Turnover_Rate)", "required": ["Inventory_Turnover_Rate"], "python_fn": "engine.get_kpis", "field": "average_turnover"},
    {"id": "low_stock_count", "name": "Low Stock Count", "category": "Basic", "formula": "COUNT(Stock_Quantity <= Reorder_Level)", "required": ["Stock_Quantity", "Reorder_Level"], "python_fn": "engine.get_kpis", "field": "low_stock"},

    # ================= INVENTORY =================
    {"id": "overstock_count", "name": "Overstock Items", "category": "Inventory", "formula": "COUNT(Stock > Reorder_Level × 3)", "required": ["Stock_Quantity", "Reorder_Level"], "python_fn": "engine.get_overstock", "list": True},
    {"id": "dead_stock", "name": "Dead Stock (Value at Risk)", "category": "Inventory", "formula": "SUM(Stock × Price) WHERE Stock > 0 AND Sales = 0", "required": ["Stock_Quantity", "Sales_Volume", "Unit_Price"], "python_fn": "engine.get_dead_stock", "nested": True},
    {"id": "reorder_critical", "name": "Critical Reorder Items", "category": "Inventory", "formula": "COUNT(Stock <= Reorder_Point)", "required": ["Stock_Quantity"], "python_fn": "engine.get_reorder_points", "nested": True},
    {"id": "business_score", "name": "Business Health Score", "category": "Inventory", "formula": "100 - (low_stock% × 0.4 + overstock% × 0.2 + expiry% × 0.4)", "required": ["Stock_Quantity", "Reorder_Level"], "python_fn": "engine.get_business_score", "nested": True},

    # ================= ABC =================
    {"id": "abc_tier_a", "name": "ABC — Tier A Products", "category": "ABC", "formula": "Cumulative Sales % <= 80", "required": ["Product_Name", "Sales_Volume"], "python_fn": "engine.get_abc_analysis", "nested": True},
    {"id": "abc_tier_b", "name": "ABC — Tier B Products", "category": "ABC", "formula": "Cumulative Sales % between 80 and 95", "required": ["Product_Name", "Sales_Volume"], "python_fn": "engine.get_abc_analysis", "nested": True},
    {"id": "abc_tier_c", "name": "ABC — Tier C Products", "category": "ABC", "formula": "Cumulative Sales % > 95", "required": ["Product_Name", "Sales_Volume"], "python_fn": "engine.get_abc_analysis", "nested": True},

    # ================= EXPIRY =================
    {"id": "expired_count", "name": "Expired Products", "category": "Expiry", "formula": "COUNT(Expiration_Date < Today)", "required": ["Expiration_Date"], "python_fn": "engine.get_expiry_analysis", "nested": True},
    {"id": "expiring_7", "name": "Expiring in 7 Days", "category": "Expiry", "formula": "COUNT(0 <= Days_Left <= 7)", "required": ["Expiration_Date"], "python_fn": "engine.get_expiry_analysis", "nested": True},
    {"id": "expiring_30", "name": "Expiring in 30 Days", "category": "Expiry", "formula": "COUNT(0 <= Days_Left <= 30)", "required": ["Expiration_Date"], "python_fn": "engine.get_expiry_analysis", "nested": True},

    # ================= SALES =================
    {"id": "top_products", "name": "Top 10 Selling Products", "category": "Sales", "formula": "Rank by SUM(Sales_Volume) DESC", "required": ["Product_Name", "Sales_Volume"], "python_fn": "engine.get_top_selling_products", "list": True},
    {"id": "low_products", "name": "Bottom 10 Selling Products", "category": "Sales", "formula": "Rank by SUM(Sales_Volume) ASC", "required": ["Product_Name", "Sales_Volume"], "python_fn": "engine.get_low_selling_products", "list": True},
    {"id": "category_perf", "name": "Category Performance", "category": "Sales", "formula": "GROUP BY Category, SUM(Sales_Volume)", "required": ["Catagory", "Sales_Volume"], "python_fn": "engine.get_category_analysis", "list": True},

    # ================= SUPPLIER =================
    {"id": "supplier_portfolio", "name": "Supplier Portfolio", "category": "Supplier", "formula": "GROUP BY Supplier_Name, COUNT(*)", "required": ["Supplier_Name"], "python_fn": "engine.get_supplier_analysis", "list": True},
    {"id": "supplier_score", "name": "Supplier Scorecard", "category": "Supplier", "formula": "Score = Contribution(50) + (50 - RiskPenalty)", "required": ["Supplier_Name", "Stock_Quantity"], "python_fn": "engine.get_supplier_scorecard", "list": True},

    # ================= FORECASTING =================
    {"id": "sales_forecast", "name": "Sales Forecast (7-day)", "category": "Forecasting", "formula": "Linear Regression on Daily Sales", "required": ["Sales_Volume", "Date_Received"], "python_fn": "ml_engine.sales_forecast", "nested": True},

    # ================= WHAT IF =================
    {"id": "what_if", "name": "What-If Simulation", "category": "Simulation", "formula": "New Revenue = (Price × (1+ΔP)) × (Sales × (1+ΔS))", "required": ["Sales_Volume", "Unit_Price"], "python_fn": "engine.get_what_if_simulator", "nested": True},
]


def get_all_calculations():
    """Return the metric registry for the Calculation Engine page."""
    return CALCULATIONS


def get_categories():
    """Return the unique categories."""
    cats = []
    for c in CALCULATIONS:
        if c["category"] not in cats:
            cats.append(c["category"])
    return cats