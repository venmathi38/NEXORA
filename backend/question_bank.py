"""
NEXORA AI — Question Bank
Maps 200+ natural-language question patterns to intents.
Used by ml_engine.ask_dataset_question_v2 for intent recognition.
"""

# Each entry: (list_of_keyword_patterns, intent_id)
# An intent matches if any pattern appears in the lowercased question.

QUESTION_PATTERNS = [
    # ---------- LOW STOCK / REORDER ----------
    (["low stock", "running out", "running low", "stock low", "nearly empty"], "low_stock"),
    (["reorder", "need to order", "should i order", "buy more", "replenish"], "low_stock"),
    (["out of stock", "zero stock", "stockout", "nothing left"], "out_of_stock"),
    (["critical stock", "critical items", "urgent stock"], "low_stock"),
    (["what to order", "what should i order", "order list", "purchase list"], "low_stock"),
    (["restock", "restocking", "refill"], "low_stock"),
    (["stock alert", "stock alerts", "stock warning"], "low_stock"),
    (["minimum stock", "below minimum", "below reorder"], "low_stock"),

    # ---------- OVERSTOCK ----------
    (["overstock", "too much stock", "excess", "surplus"], "overstock"),
    (["too much inventory", "over inventory", "overstocked"], "overstock"),
    (["excess units", "excess inventory", "excess products"], "overstock"),
    (["dead stock", "dead inventory", "idle stock"], "dead_stock"),
    (["not moving", "not selling", "slow movers", "slow selling"], "dead_stock"),
    (["sitting in warehouse", "unsold items", "unsold stock"], "dead_stock"),

    # ---------- EXPIRY ----------
    (["expiry", "expiring", "expire", "expires", "expired"], "expiry_alerts"),
    (["expiring soon", "expiring this week", "about to expire"], "expiry_soon"),
    (["expiring today", "expires today"], "expiry_today"),
    (["expiring in 7 days", "expiring next week", "expiry next week"], "expiry_soon"),
    (["expiring in 30 days", "expiry month", "expiring this month"], "expiry_month"),
    (["expired products", "expired items", "expired stock"], "expired"),
    (["date of expiry", "expiration date", "expiry date"], "expiry_alerts"),
    (["what expires", "which products expire"], "expiry_alerts"),
    (["freshness", "shelf life"], "expiry_alerts"),

    # ---------- TOTAL STOCK ----------
    (["total stock", "stock total", "how much stock"], "total_stock"),
    (["how many units", "total units", "units in stock"], "total_stock"),
    (["inventory count", "current inventory", "inventory size"], "total_stock"),
    (["stock on hand", "available stock", "available units"], "total_stock"),

    # ---------- TOTAL SALES ----------
    (["total sales", "sales total", "how much sold"], "total_sales"),
    (["total revenue", "revenue", "turnover"], "total_revenue"),
    (["sales volume", "units sold", "total units sold"], "total_sales"),
    (["how many sold", "how much did we sell"], "total_sales"),
    (["best selling", "top seller", "best seller"], "top_selling"),
    (["worst selling", "least sold", "worst seller"], "low_selling"),
    (["top products", "top selling products", "best products"], "top_selling"),
    (["slow products", "slowest products", "low selling"], "low_selling"),
    (["sales growth", "revenue growth", "growth rate"], "sales_growth"),

    # ---------- PRICE / VALUE ----------
    (["inventory value", "stock value", "value of stock"], "inventory_value"),
    (["total value", "total worth", "value"], "inventory_value"),
    (["average price", "avg price", "mean price"], "avg_price"),
    (["highest price", "most expensive", "priciest"], "highest_price"),
    (["lowest price", "cheapest", "least expensive"], "lowest_price"),
    (["currency", "currency code", "currencies"], "currency"),

    # ---------- CATEGORIES ----------
    (["category", "categories", "product category"], "category_summary"),
    (["top category", "best category", "leading category"], "top_category"),
    (["worst category", "lowest category"], "worst_category"),
    (["category performance", "category sales"], "category_summary"),
    (["how many categories", "number of categories"], "category_count"),
    (["category breakdown", "category split"], "category_summary"),

    # ---------- SUPPLIERS ----------
    (["supplier", "suppliers", "vendor", "vendors"], "supplier_summary"),
    (["top supplier", "best supplier"], "top_supplier"),
    (["supplier risk", "supplier reliability"], "supplier_summary"),
    (["how many suppliers", "number of suppliers"], "supplier_count"),
    (["supplier products", "products by supplier"], "supplier_summary"),

    # ---------- PRODUCTS ----------
    (["how many products", "product count", "total products"], "product_count"),
    (["unique products", "distinct products"], "product_count"),
    (["list products", "show products", "show me products"], "list_products"),
    (["product details", "product info", "product information"], "product_details"),

    # ---------- SEARCH SPECIFIC PRODUCT ----------
    (["search", "find", "look for", "where is", "details of", "info about"], "search_product"),
    (["tell me about", "show me"], "search_product"),
    (["price of", "cost of", "stock of"], "search_product"),
    (["supplier of", "who supplies"], "search_product"),

    # ---------- ABC ----------
    (["abc", "abc analysis", "pareto"], "abc_analysis"),
    (["80 20", "pareto principle"], "abc_analysis"),
    (["tier a", "top tier products"], "abc_analysis"),
    (["tier c", "low priority products"], "abc_analysis"),

    # ---------- BUSINESS ----------
    (["business score", "business health", "business performance"], "business_score"),
    (["business summary", "business report", "overview of business"], "business_summary"),
    (["what should i do", "recommend", "recommendation", "advice"], "recommendations"),
    (["improve business", "how to improve", "growth advice"], "recommendations"),
    (["risk", "risks", "business risk", "critical issues"], "business_risk"),
    (["problem", "problems", "issues"], "business_risk"),
    (["health check", "status check", "diagnostic"], "business_summary"),

    # ---------- RECOMMENDATIONS ----------
    (["reorder now", "replenish now", "urgent order"], "low_stock"),
    (["stop buying", "reduce purchases", "cut back"], "overstock"),
    (["promote", "promotion", "discount", "clear stock"], "dead_stock"),
    (["which product to promote", "what to discount"], "dead_stock"),
    (["what sells best", "fast movers", "fast moving"], "top_selling"),

    # ---------- DATE / TIME ----------
    (["today", "as of today", "current status"], "business_summary"),
    (["this month", "current month"], "business_summary"),
    (["last month", "previous month"], "business_summary"),
    (["this week", "current week"], "business_summary"),
    (["this year", "current year"], "business_summary"),

    # ---------- FOLLOW-UPS / COMPARISONS ----------
    (["those", "them", "same", "these"], "followup"),
    (["more details", "tell me more", "explain"], "followup"),
    (["compare", "vs ", "versus", "difference between"], "compare_products"),
    (["and ", "also ", "plus "], "followup"),

    # ---------- HELP / GREETING ----------
    (["help", "what can you do", "capabilities", "commands"], "help"),
    (["hi", "hello", "hey", "good morning", "good evening"], "greeting"),
    (["thank", "thanks", "thank you"], "greeting"),
    (["who are you", "what are you", "your name"], "greeting"),

    # ---------- ADDITIONAL VARIATIONS (single-word / short) ----------
    (["stock"], "total_stock"),
    (["sales"], "total_sales"),
    (["revenue"], "total_revenue"),
    (["expiry"], "expiry_alerts"),
    (["category"], "category_summary"),
    (["supplier"], "supplier_summary"),
    (["product"], "product_count"),
    (["value"], "inventory_value"),
    (["abc"], "abc_analysis"),
    (["risk"], "business_risk"),
    (["recommend"], "recommendations"),

    # ---------- MORE PHRASINGS ----------
    (["how is business", "how are we doing", "how are sales"], "business_summary"),
    (["how many items", "how many skus"], "product_count"),
    (["what is running out", "running out of"], "low_stock"),
    (["which need reordering", "needs reorder"], "low_stock"),
    (["what is expiring", "what expires"], "expiry_alerts"),
    (["worst inventory", "worst stock"], "dead_stock"),
    (["inventory turnover", "turnover rate"], "business_summary"),
    (["show me inventory", "show inventory"], "total_stock"),
    (["show me sales", "show sales"], "total_sales"),
    (["top 10 products", "top ten products"], "top_selling"),
    (["bottom products", "bottom sellers"], "low_selling"),
    (["most valuable product", "highest value"], "highest_price"),
    (["least valuable product", "lowest value"], "lowest_price"),
    (["category with most sales", "best performing category"], "top_category"),
    (["category with least sales", "worst performing category"], "worst_category"),
    (["supplier with most products", "biggest supplier"], "top_supplier"),
    (["what to focus on", "where to focus"], "recommendations"),
    (["inventory overview", "inventory summary"], "total_stock"),
    (["sales overview", "sales summary"], "total_sales"),
    (["stock overview", "stock summary"], "total_stock"),
    (["give me a report", "generate report"], "business_summary"),
    (["daily summary", "daily report"], "business_summary"),
    (["weekly summary", "weekly report"], "business_summary"),
    (["monthly summary", "monthly report"], "business_summary"),
    (["anything urgent", "urgent items"], "business_risk"),
    (["everything ok", "all good"], "business_summary"),
    (["any problems", "any issues"], "business_risk"),
    (["what should i buy", "what to buy"], "low_stock"),
    (["what should i sell", "what to sell"], "top_selling"),
    (["max stock", "maximum stock"], "overstock"),
    (["min stock", "minimum stock"], "low_stock"),
    (["highest stock", "most stock"], "total_stock"),
    (["lowest stock", "least stock"], "low_stock"),
    (["expensive products", "high price products"], "highest_price"),
    (["cheap products", "low price products"], "lowest_price"),
    (["avg turnover", "average turnover"], "business_summary"),
    (["is stock healthy", "stock health"], "business_summary"),
    (["should i reorder", "is it time to reorder"], "low_stock"),
    (["which items are dead", "dead items"], "dead_stock"),
    (["top selling sku", "best sku"], "top_selling"),
    (["worst sku", "worst selling sku"], "low_selling"),
    (["product mix", "product variety"], "product_count"),
    (["sku count", "how many skus"], "product_count"),
    (["price range", "price distribution"], "avg_price"),
    (["discount candidates", "markdown candidates"], "dead_stock"),
    (["promotion candidates", "promo candidates"], "dead_stock"),
    (["highest revenue product", "top revenue product"], "top_selling"),
    (["lowest revenue product", "bottom revenue product"], "low_selling"),
    (["any alerts", "show alerts"], "business_risk"),
    (["stock alerts today", "today's alerts"], "low_stock"),
    (["inventory alert", "inventory alerts"], "business_risk"),
    (["stock replenishment", "replenishment"], "low_stock"),
    (["what is overstocked", "over stocked"], "overstock"),
    (["which product is best", "best product"], "top_selling"),
    (["which product is worst", "worst product"], "low_selling"),
    (["how many expired", "count expired"], "expired"),
    (["how many expiring", "count expiring"], "expiry_alerts"),
    (["expiring count", "expired count"], "expiry_alerts"),
    (["average stock", "mean stock"], "total_stock"),
    (["peak sales", "highest sales"], "top_selling"),
    (["summary", "overview"], "business_summary"),
    (["insights", "insight"], "business_summary"),
    (["overview"], "business_summary"),
    (["deep dive", "detailed analysis"], "business_summary"),
    (["show all", "show everything"], "business_summary"),
]


def detect_intent(question: str) -> str:
    """Match a question to an intent using the pattern list. Default: unknown."""
    if not question:
        return "unknown"

    text = str(question).strip().lower()

    # Score each intent by number of patterns matched (higher score wins)
    scores = {}
    for patterns, intent in QUESTION_PATTERNS:
        for pattern in patterns:
            if pattern in text:
                scores[intent] = scores.get(intent, 0) + 1

    if not scores:
        return "unknown"

    # Return highest-scoring intent
    return max(scores, key=scores.get)


def list_all_intents():
    """Return the set of unique intents."""
    return sorted({intent for _, intent in QUESTION_PATTERNS})


def count_patterns():
    """Return the total number of question patterns loaded."""
    return sum(len(patterns) for patterns, _ in QUESTION_PATTERNS)