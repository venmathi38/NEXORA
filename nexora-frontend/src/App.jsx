import React, { useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import * as XLSX from "xlsx";
import {
  LayoutDashboard, Package, ChartNoAxesCombined, BrainCircuit, Database,
  Truck, ShieldAlert, Settings, Search, Bell, UploadCloud, FileSpreadsheet,
  ChevronRight, Menu, X, CheckCircle2, Clock3, TrendingUp, BarChart3,
  Zap, FileDown, CircleHelp, Layers3, ScanSearch, Sparkles, RefreshCw,
  Boxes, Activity, AlertTriangle, CircleDollarSign, Star
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Tooltip,
  CartesianGrid, XAxis, YAxis, LineChart, Line
} from "recharts";
import "./App.css";

const API = "http://127.0.0.1:8000";
const COLORS = ["#d8bd83", "#58b9aa", "#8b9de0", "#d58c9b", "#a99bd7"];

// 200+ question library grouped by category
const QUESTION_CATEGORIES = {
  "Stock & Inventory": [
    "What should I reorder?", "Any low stock?", "Show out of stock", "Critical stock items",
    "Restock recommendations", "Stock summary", "How much stock do I have?", "How many units in inventory?",
    "Available stock", "Inventory count", "Items with zero stock", "Which products are running low?",
    "Which need reordering?", "Stock alert list", "Products below reorder level", "Inventory overview",
    "Show all stock", "Highest stock product", "Lowest stock product", "Stock health check",
    "Total stock units", "Current inventory value",
  ],
  "Sales & Revenue": [
    "Total sales", "Total revenue", "Sales volume summary", "Top selling products", "Best sellers",
    "Worst selling products", "Slow movers", "Sales overview", "How much did we sell?",
    "Best performing product", "Lowest revenue product", "Top 10 products", "Bottom 10 products",
    "Revenue breakdown", "Total units sold", "Fast moving items", "Peak sales", "Sales summary",
    "Product sales ranking", "Sales growth",
  ],
  "Expiry & Freshness": [
    "Any expiring soon?", "What expires this week?", "Show expired products", "Expiring within 7 days",
    "Expiring within 30 days", "Expiry summary", "Products about to expire", "Fresh products",
    "Shelf life check", "Expiry alerts", "Expiry count", "Expired items list", "Expiry risk products",
    "What expires today?", "Any old stock?", "Show expiring inventory", "Expiry report",
    "Upcoming expirations", "How many expired?", "Which products need urgent sale?",
  ],
  "Categories": [
    "Which category leads?", "Top category", "Best category", "Worst category", "Category breakdown",
    "Category performance", "Sales by category", "How many categories?", "Show categories",
    "Category summary", "Category comparison", "Top 5 categories", "Category revenue",
    "Leading category", "Lowest category",
  ],
  "Suppliers": [
    "Show supplier insights", "Top supplier", "Supplier summary", "Supplier performance",
    "How many suppliers?", "Supplier with most products", "Supplier risk", "Supplier breakdown",
    "Best supplier", "Supplier stock contribution", "Supplier comparison", "List suppliers",
    "Vendor overview", "Supplier dependency", "Supplier report",
  ],
  "ABC Analysis": [
    "Run ABC analysis", "ABC classification", "Pareto analysis", "Tier A products", "Tier B products",
    "Tier C products", "80 20 rule", "Top tier products", "Low priority products", "ABC breakdown",
    "Which products are Tier A?", "Classify products", "Product priority tiers",
  ],
  "Business Health": [
    "Business health summary", "Business score", "Overall business status", "Business risk summary",
    "Any problems?", "Any issues today?", "Urgent items", "Business insights", "Health check",
    "Status overview", "Daily summary", "Weekly summary", "Monthly report", "Business diagnostics",
    "Performance score", "Overall summary",
  ],
  "Recommendations": [
    "What should I do?", "Recommend actions", "Business recommendations", "How to improve sales?",
    "What to promote?", "What to discount?", "What to stop buying?", "Reduce overstock",
    "Improve inventory", "Growth advice", "Which products to promote?", "Discontinue candidates",
    "Optimize stock", "Action items",
  ],
  "Product Lookup": [
    "Tell me about Bread", "Find Egg", "Details of Milk", "Show product Bread Flour", "Price of Milk",
    "Stock of Rice", "Supplier of Egg", "Info about Cheese", "Where is Pomegranate?", "Compare two products",
  ],
  "Help & Greetings": [
    "Hello", "Hi", "What can you do?", "Help me", "What questions can I ask?", "Show commands",
    "Who are you?", "What are your capabilities?",
  ],
};

const NAVIGATION = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Sales Intelligence", icon: ChartNoAxesCombined },
  { label: "Inventory", icon: Package },
  { label: "Expiry Monitor", icon: ShieldAlert },
  { label: "Suppliers", icon: Truck },
  { label: "ABC Analysis", icon: Layers3 },
  { label: "Supplier Scorecard", icon: Star },
  { label: "AI Intelligence", icon: BrainCircuit },
  { label: "Data Cleaning", icon: ScanSearch },
  { label: "Data Studio", icon: Database },
  { label: "What-If Simulator", icon: Activity },
  { label: "Business Risk Map", icon: AlertTriangle },
  { label: "Data Storytelling", icon: FileDown },
  { label: "Business Report", icon: FileDown },
  { label: "Calculations", icon: CircleHelp }
];

const aliases = {
  product: ["product_name", "product", "item_name"],
  category: ["category", "catagory", "product_category"],
  stock: ["stock_quantity", "stock", "quantity", "current_stock"],
  reorder: ["reorder_level", "reorder_point", "minimum_stock"],
  sales: ["sales_volume", "sales", "quantity_sold"],
  price: ["unit_price", "price", "selling_price"],
  supplier: ["supplier_name", "supplier", "vendor"],
  expiry: ["expiration_date", "expiry_date", "expiry"],
  turnover: ["inventory_turnover_rate", "turnover_rate", "turnover"],
  location: ["warehouse_location", "location", "warehouse"]
};

const normalize = (value) => String(value ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");
const findColumn = (rows, key) => {
  if (!rows.length) return null;
  const columns = Object.keys(rows[0]);
  return columns.find((column) => aliases[key]?.some((alias) => normalize(alias) === normalize(column))) || null;
};
const number = (value) => {
  const text = String(value ?? "").trim();
  if (!text) return 0;
  const negative = /^\(.*\)$/.test(text);
  const parsed = Number(text.replace(/[,$€£₹\s()]/g, ""));
  return Number.isFinite(parsed) ? (negative ? -Math.abs(parsed) : parsed) : 0;
};
const isNumericValue = (value) => {
  if (value === null || value === undefined || String(value).trim() === "") return false;
  const text = String(value).trim();
  return Number.isFinite(Number(text.replace(/[,$€£₹\s()]/g, "")));
};

function parseDate(value) {
  if (!value) return null;
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  const text = String(value).trim();
  const iso = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (iso) {
    const year = Number(iso[1]);
    const month = Number(iso[2]);
    const day = Number(iso[3]);
    const date = new Date(year, month - 1, day);
    if (month < 1 || month > 12 || date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
    return date;
  }
  const dmy = text.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
  if (dmy) {
    const first = Number(dmy[1]);
    const second = Number(dmy[2]);
    const year = Number(dmy[3]);
    if (first <= 12 && second <= 12) return null;
    const day = first > 12 ? first : second;
    const month = first > 12 ? second : first;
    const date = new Date(year, month - 1, day);
    if (month < 1 || month > 12 || date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
    return date;
  }
  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

const unknownCurrencyValue = (value) => value === null || value === undefined
  ? "N/A"
  : `${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })} · Unknown currency`;

function getAnalytics(rows, dashboard) {
  const productCol = findColumn(rows, "product");
  const categoryCol = findColumn(rows, "category");
  const stockCol = findColumn(rows, "stock");
  const reorderCol = findColumn(rows, "reorder");
  const salesCol = findColumn(rows, "sales");
  const priceCol = findColumn(rows, "price");
  const supplierCol = findColumn(rows, "supplier");
  const expiryCol = findColumn(rows, "expiry");

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const expiryItems = expiryCol
    ? rows.map((row) => ({ ...row, _expiryDate: parseDate(row[expiryCol]) })).filter((row) => row._expiryDate)
    : [];

  const expired = expiryItems.filter((row) => row._expiryDate < today);
  const expiringSoon = expiryItems.filter((row) => {
    const expiryDate = new Date(row._expiryDate);
    expiryDate.setHours(0, 0, 0, 0);
    const days = Math.round((expiryDate.getTime() - today.getTime()) / 86400000);
    return days >= 0 && days <= 30;
  });

  const columns = rows.length ? Object.keys(rows[0]) : [];
  const numericKeys = ["stock", "reorder", "sales", "price", "turnover"];
  const dateKeys = ["expiry"];
  const columnQuality = columns.map((column) => {
    const values = rows.map((row) => row[column]);
    const missing = values.filter((value) => value === null || value === undefined || String(value).trim() === "").length;
    const numeric = numericKeys.some((key) => aliases[key]?.some((alias) => normalize(alias) === normalize(column)));
    const date = dateKeys.some((key) => aliases[key]?.some((alias) => normalize(alias) === normalize(column)));
    const invalid = numeric
      ? values.filter((value) => value !== null && value !== undefined && String(value).trim() !== "" && !isNumericValue(value)).length
      : date
        ? values.filter((value) => value !== null && value !== undefined && String(value).trim() !== "" && !parseDate(value)).length
        : 0;
    const ambiguousDates = date
      ? values.filter((value) => /^(\d{1,2})[-/](\d{1,2})[-/]\d{4}$/.test(String(value ?? "").trim()) &&
        Number(String(value).trim().split(/[-/]/)[0]) <= 12 && Number(String(value).trim().split(/[-/]/)[1]) <= 12).length
      : 0;
    return { column, missing, invalid, ambiguousDates };
  });
  const totalCells = rows.length * columns.length;
  const missingCells = columnQuality.reduce((sum, item) => sum + item.missing, 0);
  const dataQuality = totalCells ? Math.round((totalCells - missingCells) / totalCells * 100) : 0;

  const uniqueProducts = productCol
    ? new Set(rows.map((row) => String(row[productCol] || "").trim()).filter(Boolean)).size
    : rows.length;

  const expiryAnalysis = dashboard?.expiry_analysis;
  const expiryRecords = expiryAnalysis?.records || [];
  const expiryCounts = expiryAnalysis?.counts || {};

  const apiCategories = dashboard?.category_analysis?.map((record) => {
    const name = String(record[categoryCol] ?? "Uncategorized");
    const value = salesCol && record[salesCol] != null ? Number(record[salesCol]) : stockCol && record[stockCol] != null ? Number(record[stockCol]) : Number(record.count || 0);
    return { name, value: Number.isFinite(value) ? value : 0 };
  });

  const apiSuppliers = dashboard?.supplier_analysis?.map((record) => ({
    name: String(record[supplierCol] ?? "Unknown"),
    products: Number(record.total_products || 0)
  })).sort((a, b) => b.products - a.products).slice(0, 6);

  const apiTopProducts = dashboard?.top_selling?.map((record) => ({
    name: String(record[productCol] ?? "Unknown"),
    sales: Number(record[salesCol] || 0)
  }));

  const apiQuality = dashboard?.quality?.map((item) => ({
    column: item.column, missing: item.missing_values, invalid: item.invalid_values, ambiguousDates: item.ambiguous_dates
  }));

  const qualityMissing = apiQuality?.reduce((sum, item) => sum + Number(item.missing || 0), 0);
  const serverKpis = dashboard?.kpis;

  return {
    productCol, categoryCol, stockCol, reorderCol, salesCol, priceCol, supplierCol, expiryCol,
    expiryRecognised: (expiryCounts.Expired || 0) + (expiryCounts["Expiring within 7 days"] || 0) + (expiryCounts["Expiring within 30 days"] || 0) + (expiryCounts.Valid || 0),
    expirySummary: expiryCounts,
    expiryRecords,
    totalStock: serverKpis?.total_stock ?? 0,
    totalSales: serverKpis?.total_sales ?? 0,
    inventoryValue: serverKpis?.inventory_value ?? null,
    estimatedSalesValue: serverKpis?.estimated_sales_value ?? null,
    currency: serverKpis?.currency || "Unknown currency",
    lowStock: dashboard?.low_stock ?? [],
    overstock: dashboard?.overstock ?? [],
    expired: expiryRecords.filter((item) => item.expiry_status === "Expired"),
    expiringSoon: expiryRecords.filter((item) => ["Expiring within 7 days", "Expiring within 30 days"].includes(item.expiry_status)),
    expiring7: expiryAnalysis ? expiryRecords.filter((item) => item.expiry_status === "Expiring within 7 days") : [],
    expiring8to30: expiryAnalysis ? expiryRecords.filter((item) => item.expiry_status === "Expiring within 30 days") : [],
    validExpiry: expiryRecords.filter((item) => item.expiry_status === "Valid"),
    ambiguousExpiry: expiryRecords.filter((item) => item.expiry_status === "Ambiguous"),
    missingExpiry: expiryRecords.filter((item) => item.expiry_status === "Missing"),
    categories: apiCategories ?? [],
    suppliers: apiSuppliers ?? [],
    topProducts: apiTopProducts ?? [],
    columnQuality: apiQuality ?? [],
    dataQuality: dashboard && totalCells ? Math.round((totalCells - qualityMissing) / totalCells * 100) : 0,
    uniqueProducts: serverKpis?.total_products ?? 0
  };
}

function createInsights(stats) {
  const list = [];
  if (stats.lowStock.length) list.push({ type: "warning", title: "Reorder attention required", detail: `${stats.lowStock.length} products are at or below their reorder level.`, icon: AlertTriangle });
  if (stats.expired.length) list.push({ type: "danger", title: "Expired stock detected", detail: `${stats.expired.length} records have an expiry date before today.`, icon: ShieldAlert });
  if (stats.expiringSoon.length) list.push({ type: "warning", title: "Upcoming expiry risk", detail: `${stats.expiringSoon.length} products expire within the next 30 days.`, icon: Clock3 });
  if (stats.overstock.length) list.push({ type: "info", title: "Possible overstock", detail: `${stats.overstock.length} products have stock above three times their reorder level.`, icon: Boxes });
  const missingChecks = [];
  if (!stats.stockCol || !stats.reorderCol) missingChecks.push("stock and reorder");
  if (!stats.expiryCol) missingChecks.push("expiry");
  if (missingChecks.length) list.push({ type: "info", title: "Some checks are unavailable", detail: `Upload data with ${missingChecks.join(" and ")} columns to enable all inventory alerts.`, icon: AlertTriangle });
  if (!list.length) list.push({ type: "success", title: "No major inventory alerts", detail: "No low-stock, overstock or expiry alerts were identified.", icon: CheckCircle2 });
  return list;
}

function App() {
  const fileInput = useRef(null);
  const [rows, setRows] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [fileName, setFileName] = useState("");
  const [activePage, setActivePage] = useState("Overview");
  const [uploadError, setUploadError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [mlLoading, setMlLoading] = useState(false);
  const [mlReport, setMlReport] = useState(null);
  const [mlRisk, setMlRisk] = useState([]);
  const [mlAnomalies, setMlAnomalies] = useState([]);
  const [mlRecommendations, setMlRecommendations] = useState([]);
  const [mlPerformance, setMlPerformance] = useState(null);
  const [backendStatus, setBackendStatus] = useState("Connecting...");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [cleanReport, setCleanReport] = useState(null);
  const [cleanLoading, setCleanLoading] = useState(false);
  const [cleanSelected, setCleanSelected] = useState({});
  const [cleanResult, setCleanResult] = useState(null);
  const [abcData, setAbcData] = useState(null);
  const [abcLoading, setAbcLoading] = useState(false);
  const [deadStockData, setDeadStockData] = useState(null);
  const [deadStockLoading, setDeadStockLoading] = useState(false);
  const [heatmapData, setHeatmapData] = useState(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [reorderData, setReorderData] = useState(null);
  const [reorderLoading, setReorderLoading] = useState(false);
  const [supplierScoreData, setSupplierScoreData] = useState(null);
  const [supplierScoreLoading, setSupplierScoreLoading] = useState(false);
  const [whatIfData, setWhatIfData] = useState(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [priceChange, setPriceChange] = useState(0);
  const [salesChange, setSalesChange] = useState(0);
  const [riskMapData, setRiskMapData] = useState(null);
  const [riskMapLoading, setRiskMapLoading] = useState(false);
  const [storyData, setStoryData] = useState(null);
  const [storyLoading, setStoryLoading] = useState(false);
  const [copilotHistory, setCopilotHistory] = useState([]);
  const [copilotIntent, setCopilotIntent] = useState("");
  const [calcList, setCalcList] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcSelected, setCalcSelected] = useState(null);
  const [calcResult, setCalcResult] = useState(null);
  const [calcCategory, setCalcCategory] = useState("All");
  const [reportTheme, setReportTheme] = useState("dark");
  const [pdfGenerating, setPdfGenerating] = useState(false);
  const [questionCategory, setQuestionCategory] = useState("Stock & Inventory");
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    try { return localStorage.getItem("nexora_auth") === "true"; } catch { return false; }
  });
  const [authMode, setAuthMode] = useState("signin");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "", remember: true });

  const stats = useMemo(() => getAnalytics(rows, dashboard), [rows, dashboard]);
  const insights = useMemo(() => createInsights(stats), [stats]);

  useEffect(() => {
    let alive = true;
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API}/api/health`);
        if (!response.ok) throw new Error("Backend unavailable");
        if (alive) setBackendStatus("Backend connected");
      } catch {
        if (alive) setBackendStatus("Backend disconnected");
      }
    };
    checkBackend();
    const timer = setInterval(checkBackend, 15000);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  const loadMLInsights = async () => {
    setMlLoading(true);
    try {
      const endpoints = ["/api/ai/report", "/api/ai/risk", "/api/ai/anomalies", "/api/ai/recommendations", "/api/ai/performance"];
      const results = await Promise.allSettled(endpoints.map(async (path) => {
        const response = await fetch(`${API}${path}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `${path} failed`);
        return data;
      }));
      const getResult = (index, fallback) => results[index].status === "fulfilled" ? results[index].value : fallback;
      setMlReport(getResult(0, {}));
      setMlRisk(getResult(1, { records: [] }).records || []);
      setMlAnomalies(getResult(2, { records: [] }).records || []);
      setMlRecommendations(getResult(3, { recommendations: [] }).recommendations || []);
      setMlPerformance(getResult(4, {}));
      const failedCount = results.filter((result) => result.status === "rejected").length;
      if (failedCount > 0) setAnswer(`${failedCount} ML analysis service(s) failed. Other results were loaded.`);
    } catch (error) {
      setAnswer(`ML analysis error: ${error.message}`);
    } finally {
      setMlLoading(false);
    }
  };

  const uploadFile = async (file) => {
    if (!file) return;
    setUploadError("");
    setAnswer("");
    const extension = file.name.split(".").pop().toLowerCase();
    if (!["csv", "xlsx", "xls"].includes(extension)) { setUploadError("Please upload a CSV, XLS or XLSX file."); return; }
    try {
      let parsedRows = [];
      if (extension === "csv") {
        parsedRows = await new Promise((resolve, reject) => {
          Papa.parse(file, { header: true, skipEmptyLines: true, dynamicTyping: false, complete: (result) => resolve(result.data), error: reject });
        });
      } else {
        const buffer = await file.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array", cellDates: true });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        parsedRows = XLSX.utils.sheet_to_json(firstSheet, { defval: "" });
      }
      parsedRows = parsedRows.filter((row) => Object.values(row).some((value) => String(value ?? "").trim() !== ""));
      if (!parsedRows.length) throw new Error("No usable rows were found in this file.");

      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API}/api/upload`, { method: "POST", body: formData });
      if (!response.ok) { const errorData = await response.json().catch(() => ({})); throw new Error(errorData.detail || "Backend dataset upload failed."); }
      const dashboardResponse = await fetch(`${API}/api/dashboard`);
      const dashboardData = await dashboardResponse.json();
      if (!dashboardResponse.ok) throw new Error(dashboardData.detail || "Dashboard metrics could not be loaded.");

      setDashboard(dashboardData);
      setRows(parsedRows);
      setFileName(file.name);
      setActivePage("Overview");
      setMlReport(null); setMlRisk([]); setMlAnomalies([]); setMlRecommendations([]); setMlPerformance(null);
      setAnswer("Dataset uploaded successfully. Loading ML analysis...");
      await loadMLInsights();
      setAnswer("Dataset uploaded successfully. ML analysis is complete.");
    } catch (error) {
      console.error("Dataset upload error:", error);
      setUploadError(error.message || "Unable to upload dataset.");
      setBackendStatus("Backend disconnected");
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const downloadReport = () => {
    if (!rows.length) return;
    const report = [["NEXORA AI — Inventory Intelligence Report"], ["Dataset", fileName], ["Rows", rows.length], ["Unique products", stats.uniqueProducts], ["Total stock", stats.totalStock], ["Total sales volume", stats.totalSales], ["Low stock records", stats.lowStock.length], ["Overstock records", stats.overstock.length], ["Expired records", stats.expired.length], ["Expiring within 30 days", stats.expiringSoon.length], ["Data completeness", `${stats.dataQuality}%`]];
    const csv = report.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = "NEXORA_Intelligence_Report.csv"; link.click(); URL.revokeObjectURL(url);
  };

  const analyzeCleaning = async () => {
    if (!rows.length) { setUploadError("Please upload a dataset first."); return; }
    setCleanLoading(true); setCleanResult(null);
    try {
      const res = await fetch(`${API}/api/clean/analyze`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Cleaning analysis failed.");
      setCleanReport(data);
      const initial = {};
      (data.issues || []).forEach((iss) => { initial[iss.id] = !!iss.fixable; });
      setCleanSelected(initial);
    } catch (err) { setUploadError(`Cleaning analysis error: ${err.message}`); } finally { setCleanLoading(false); }
  };

  const applyCleaning = async () => {
    const fixIds = Object.keys(cleanSelected).filter((k) => cleanSelected[k]);
    setCleanLoading(true);
    try {
      const res = await fetch(`${API}/api/clean/apply`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fix_ids: fixIds }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Cleaning apply failed.");
      setCleanResult(data);
    } catch (err) { setUploadError(`Cleaning apply error: ${err.message}`); } finally { setCleanLoading(false); }
  };

  const downloadCleaned = () => { if (cleanResult?.token) window.open(`${API}/api/clean/download/${cleanResult.token}`, "_blank"); };
  const loadAbcAnalysis = async () => { setAbcLoading(true); try { const res = await fetch(`${API}/api/analytics/abc`); const data = await res.json(); if (!res.ok) throw new Error(data.detail); setAbcData(data); } catch (err) { setUploadError(`ABC error: ${err.message}`); } finally { setAbcLoading(false); } };
  const loadDeadStock = async () => { setDeadStockLoading(true); try { const res = await fetch(`${API}/api/analytics/dead-stock`); const data = await res.json(); if (!res.ok) throw new Error(data.detail); setDeadStockData(data); } catch (err) { setUploadError(`Dead stock error: ${err.message}`); } finally { setDeadStockLoading(false); } };
  const loadHeatmap = async () => { setHeatmapLoading(true); try { const res = await fetch(`${API}/api/analytics/category-heatmap`); const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Heatmap failed."); setHeatmapData(data); } catch (err) { setUploadError(`Heatmap error: ${err.message}`); } finally { setHeatmapLoading(false); } };
  const loadReorderPoints = async () => { setReorderLoading(true); try { const res = await fetch(`${API}/api/analytics/reorder-points`); const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Reorder points failed."); setReorderData(data); } catch (err) { setUploadError(`Reorder points error: ${err.message}`); } finally { setReorderLoading(false); } };
  const loadSupplierScorecard = async () => { setSupplierScoreLoading(true); try { const res = await fetch(`${API}/api/analytics/supplier-scorecard`); const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Supplier scorecard failed."); setSupplierScoreData(data); } catch (err) { setUploadError(`Supplier scorecard error: ${err.message}`); } finally { setSupplierScoreLoading(false); } };

  const loadWhatIf = async () => {
    setWhatIfLoading(true);
    try {
      const res = await fetch(`${API}/api/analytics/what-if`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ price_change_pct: priceChange, sales_change_pct: salesChange })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setWhatIfData(data);
    } catch (err) { setUploadError(`What-if error: ${err.message}`); } finally { setWhatIfLoading(false); }
  };

  const loadRiskMap = async () => {
    setRiskMapLoading(true);
    try {
      const res = await fetch(`${API}/api/analytics/risk-map`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setRiskMapData(data);
    } catch (err) { setUploadError(`Risk map error: ${err.message}`); } finally { setRiskMapLoading(false); }
  };

  const loadStory = async () => {
    setStoryLoading(true);
    try {
      const res = await fetch(`${API}/api/analytics/story`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setStoryData(data);
    } catch (err) { setUploadError(`Story error: ${err.message}`); } finally { setStoryLoading(false); }
  };

  const askCopilot = async (questionText) => {
    const q = (questionText ?? question).trim();
    if (!q) { setAnswer("Please enter a question."); return; }
    if (!rows.length) { setAnswer("Please upload a dataset first."); return; }
    setAiLoading(true);
    setAnswer("");
    setCopilotIntent("");
    try {
      const res = await fetch(`${API}/api/ai/ask-v2`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, history: copilotHistory }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Copilot error.");
      setAnswer(data);
      setCopilotIntent(data.intent || "");
      setCopilotHistory((prev) => {
        const next = [...prev, { question: q, answer: data.answer, records: data.records || [] }];
        return next.slice(-3);
      });
      setQuestion("");
    } catch (err) {
      setAnswer(`Copilot error: ${err.message}`);
    } finally {
      setAiLoading(false);
    }
  };

  const clearCopilotMemory = () => {
    setCopilotHistory([]);
    setCopilotIntent("");
    setAnswer("");
  };
  const handleAuthSubmit = (e) => {
    e.preventDefault();
    setAuthError("");

    const email = authForm.email.trim();
    const password = authForm.password.trim();
    const name = authForm.name.trim();

    if (!email || !password) {
      setAuthError("Please fill in both email and password.");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setAuthError("Please enter a valid email address.");
      return;
    }
    if (password.length < 6) {
      setAuthError("Password must be at least 6 characters.");
      return;
    }
    if (authMode === "register" && name.length < 2) {
      setAuthError("Please enter your full name.");
      return;
    }

    setAuthLoading(true);
    setTimeout(() => {
      try {
        localStorage.setItem("nexora_auth", "true");
        localStorage.setItem("nexora_user", JSON.stringify({ name: name || email.split("@")[0], email }));
      } catch {}
      setAuthLoading(false);
      setIsAuthenticated(true);
    }, 700);
  };

  const handleLogout = () => {
    try {
      localStorage.removeItem("nexora_auth");
      localStorage.removeItem("nexora_user");
    } catch {}
    setIsAuthenticated(false);
    setAuthForm({ name: "", email: "", password: "", remember: true });
    setAuthMode("signin");
  };

  const renderLogin = () => (
    <div className="login-shell">
      <div className="login-orbit one"></div>
      <div className="login-orbit two"></div>

      <div className="login-card">
        <div className="login-brand">
          <div className="login-brand-mark">N</div>
          <div className="login-brand-text">
            <strong>NEXORA</strong>
            <small>INTELLIGENCE SYSTEM</small>
          </div>
        </div>

        <div className="login-eyebrow">AI-POWERED RETAIL INTELLIGENCE</div>

        <div className="login-tabs">
          <button
            className={`login-tab ${authMode === "signin" ? "active" : ""}`}
            onClick={() => { setAuthMode("signin"); setAuthError(""); }}
            type="button"
          >
            Sign In
          </button>
          <button
            className={`login-tab ${authMode === "register" ? "active" : ""}`}
            onClick={() => { setAuthMode("register"); setAuthError(""); }}
            type="button"
          >
            Create Account
          </button>
        </div>

        {authError && <div className="login-error">{authError}</div>}

        <form onSubmit={handleAuthSubmit}>
          {authMode === "register" && (
            <div className="login-field">
              <label>Full Name</label>
              <input
                type="text"
                value={authForm.name}
                onChange={(e) => setAuthForm({ ...authForm, name: e.target.value })}
                placeholder="Your name"
              />
            </div>
          )}

          <div className="login-field">
            <label>Email Address</label>
            <input
              type="email"
              value={authForm.email}
              onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
              placeholder="you@example.com"
            />
          </div>

          <div className="login-field">
            <label>Password</label>
            <input
              type="password"
              value={authForm.password}
              onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
              placeholder="At least 6 characters"
            />
          </div>

          <div className="login-row">
            <label>
              <input
                type="checkbox"
                checked={authForm.remember}
                onChange={(e) => setAuthForm({ ...authForm, remember: e.target.checked })}
              />
              Remember me
            </label>
            <a href="#" onClick={(e) => e.preventDefault()}>Forgot password?</a>
          </div>

          <button type="submit" className="login-submit" disabled={authLoading}>
            {authLoading
              ? "Please wait..."
              : authMode === "signin"
                ? "Sign In to NEXORA"
                : "Create My Account"}
          </button>
        </form>

        <div className="login-footer">
          Powered by <strong>NEXORA AI</strong> · v1.0
        </div>
      </div>
    </div>
  );
  const loadCalculations = async () => {
    setCalcLoading(true);
    try {
      const res = await fetch(`${API}/api/calculations`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setCalcList(data);
    } catch (err) {
      setUploadError(`Calculations error: ${err.message}`);
    } finally {
      setCalcLoading(false);
    }
  };

  const runCalculation = async (calcId) => {
    setCalcSelected(calcId);
    setCalcResult(null);
    try {
      const res = await fetch(`${API}/api/calculations/result/${calcId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Calculation failed.");
      setCalcResult(data);
    } catch (err) {
      setCalcResult({ error: err.message });
    }
  };

  const downloadCleanedExcel = () => {
    if (!rows.length) return;
    window.open(`${API}/api/clean/download-excel`, "_blank");
  };

  const downloadPdfReport = async () => {
    if (!rows.length) { setUploadError("Please upload a dataset first."); return; }
    setPdfGenerating(true);
    try {
      const reportNode = document.getElementById("pdf-report-root");
      if (!reportNode) throw new Error("Report area not ready.");

      const { default: jsPDF } = await import("jspdf");
      const { default: html2canvas } = await import("html2canvas");

      const canvas = await html2canvas(reportNode, {
        scale: 2,
        backgroundColor: reportTheme === "dark" ? "#0b111c" : "#ffffff",
        useCORS: true,
      });
      const imgData = canvas.toDataURL("image/png");

      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = pageWidth;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      pdf.save(`NEXORA_Report_${fileName.replace(/\.[^.]+$/, "")}_${reportTheme}.pdf`);
    } catch (err) {
      setUploadError(`PDF error: ${err.message}`);
    } finally {
      setPdfGenerating(false);
    }
  };

  const filteredRows = rows.filter((row) => Object.values(row).some((value) => String(value).toLowerCase().includes(search.toLowerCase())));

  const renderML = () => (
    <>
      <div className="section-heading">
        <div><span className="eyebrow">MACHINE LEARNING</span><h2>Advanced Intelligence</h2></div>
        <button className="secondary-button" onClick={loadMLInsights} disabled={mlLoading || !rows.length}><Sparkles size={16} /> {mlLoading ? "Analysing..." : "Refresh insights"}</button>
      </div>
      <div className="ml-results-grid">
        <div className="panel"><PanelTitle title="Inventory Risk" subtitle="Inventory attention" /><DataTable rows={mlRisk} /></div>
        <div className="panel"><PanelTitle title="Anomaly Detection" subtitle="Unusual records identified by the model" /><DataTable rows={mlAnomalies} /></div>
        <div className="panel"><PanelTitle title="Smart Reorder" subtitle="Replenishment suggestions" /><DataTable rows={mlRecommendations} /></div>
        <div className="panel performance-panel">
          <PanelTitle title="Product Performance" subtitle="Top and bottom performing products" />
          {mlPerformance?.available ? <><h3 className="performance-heading">Top 10 Products</h3><DataTable rows={(mlPerformance.top_products || []).slice(0, 10)} /><h3 className="performance-heading">Bottom 10 Products</h3><DataTable rows={(mlPerformance.bottom_products || []).slice(0, 10)} /></> : <EmptyChart message={mlPerformance?.message || "Upload a dataset to view product performance."} />}
        </div>
      </div>
      <div className="panel ai-report-panel">
        <PanelTitle title="NEXORA AI Report" subtitle="Automated summary from your uploaded dataset" />
        {mlReport ? <div className="report-grid">{[["Inventory Analysed", mlReport.inventory_risk?.total_analysed ?? 0], ["Critical Risk", mlReport.inventory_risk?.critical ?? 0], ["Anomalies Detected", mlReport.anomaly_detection?.anomaly_count ?? 0], ["Reorder Suggestions", mlReport.reorder_recommendations?.recommendation_count ?? 0], ["Products Analysed", mlReport.product_performance?.products_analysed ?? 0]].map(([label, value]) => <div className="report-card" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div> : <EmptyChart message="Upload a dataset to generate your AI report." />}
      </div>
    </>
  );

  const renderOverview = () => (
    <>
      <div className="welcome-row"><div><div className="eyebrow"><Sparkles size={14} /> RETAIL INTELLIGENCE PLATFORM</div><h1>Business <span>Overview</span></h1><p className="subtitle">Your retail operations, understood at a glance.</p></div><button className="outline-button" onClick={downloadReport} disabled={!rows.length}><FileDown size={16} /> Export report</button></div>
      {!rows.length ? <div className="upload-hero">
        <div className="upload-orbit orbit-one"></div><div className="upload-orbit orbit-two"></div>
        <div className="upload-symbol"><UploadCloud size={32} /></div>
        <div className="eyebrow">YOUR INTELLIGENCE STARTS HERE</div><h2>Bring your retail data <span>to life.</span></h2>
        <p>Upload your shop or supermarket dataset to unlock your intelligence dashboard.</p>
        <button className="gold-button" onClick={() => fileInput.current?.click()}><UploadCloud size={17} /> Upload dataset</button>
        <div className="file-support"><FileSpreadsheet size={14} /> CSV · XLS · XLSX</div>
        {uploadError && <div className="error-message">{uploadError}</div>}
        <div className="privacy-note"><ShieldAlert size={13} /> Your original file is not modified.</div>
      </div> : <>
        <div className="dataset-banner"><div className="dataset-file"><FileSpreadsheet size={19} /></div><div><strong>{fileName}</strong><span>{rows.length.toLocaleString("en-IN")} records · Manual upload</span></div><div className="dataset-status"><span></span> ANALYSIS READY</div><button className="icon-button" title="Upload another dataset" onClick={() => fileInput.current?.click()}><RefreshCw size={17} /></button></div>
        <div className="section-heading"><div><span className="eyebrow">LIVE DATA SNAPSHOT</span><h2>Key performance indicators</h2></div><span className="updated-label"><Activity size={13} /> Calculated from uploaded data</span></div>
        <div className="kpi-grid">
          <KpiCard title="Unique products" value={stats.uniqueProducts.toLocaleString("en-IN")} icon={Package} note="Distinct product records" />
          <KpiCard title="Total stock" value={stats.totalStock.toLocaleString("en-IN")} icon={Boxes} note="Recorded stock quantity" />
          <KpiCard title="Sales volume" value={stats.totalSales.toLocaleString("en-IN")} icon={TrendingUp} note="Recorded sales volume" />
          <KpiCard title="Low stock alerts" value={stats.lowStock.length} icon={AlertTriangle} note="At or below reorder level" alert />
        </div>
        <div className="chart-grid">
          <div className="panel chart-panel"><PanelTitle title="Category intelligence" subtitle="Sales volume or record count by category" />
            {stats.categories.length ? <div className="donut-layout"><div className="donut-chart"><ResponsiveContainer width="100%" height={230}><PieChart><Pie data={stats.categories} dataKey="value" nameKey="name" innerRadius={65} outerRadius={91} paddingAngle={4}>{stats.categories.map((item, i) => <Cell key={item.name} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div><div className="legend-list">{stats.categories.slice(0, 6).map((item, i) => <div className="legend-item" key={item.name}><span style={{ background: COLORS[i % COLORS.length] }}></span><label>{item.name}</label><strong>{item.value.toLocaleString("en-IN")}</strong></div>)}</div></div> : <EmptyChart message="Category column not found in this dataset." />}
          </div>
          <div className="panel chart-panel"><PanelTitle title="Top performing products" subtitle="Ranked by recorded sales volume" />
            {stats.topProducts.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={stats.topProducts} layout="vertical" margin={{ left: 12, right: 16 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#283448" /><XAxis type="number" tick={{ fill: "#929db0", fontSize: 11 }} /><YAxis dataKey="name" type="category" width={105} tick={{ fill: "#d4d9e2", fontSize: 10 }} /><Tooltip contentStyle={{ background: "#182235", border: "1px solid #3a465a", borderRadius: 10 }} /><Bar dataKey="sales" fill="#d8bd83" radius={[0, 5, 5, 0]} barSize={16} /></BarChart></ResponsiveContainer> : <EmptyChart message="Product and sales columns are required for this chart." />}
          </div>
        </div>
        <div className="section-heading"><div><span className="eyebrow">AUTOMATED OBSERVATIONS</span><h2>Intelligence highlights</h2></div><span className="ai-tag"><Sparkles size={13} /> DATA-DRIVEN</span></div>
        <div className="insight-grid">{insights.map((item, i) => { const Icon = item.icon; return <div className={`insight-card ${item.type}`} key={i}><div className="insight-icon"><Icon size={19} /></div><div><h3>{item.title}</h3><p>{item.detail}</p></div><ChevronRight size={16} className="insight-arrow" /></div>; })}</div>
        {renderML()}
        <div className="two-column">
          <div className="panel"><PanelTitle title="Inventory health" subtitle="Stock monitoring summary" />
            {[["Low stock", stats.lowStock.length, ""], ["Possible overstock", stats.overstock.length, "teal"], ["Expired records", stats.expired.length, "red"]].map(([label, value, cls]) => <React.Fragment key={label}><div className="health-row"><span>{label}</span><strong>{value}</strong></div><div className={`health-track ${cls}`}><span style={{ width: `${Math.min(100, value / Math.max(rows.length, 1) * 100)}%` }}></span></div></React.Fragment>)}
          </div>
          <div className="panel"><PanelTitle title="Data quality" subtitle="Completeness of uploaded records" /><div className="quality-score"><div className="quality-number">{stats.dataQuality}<small>%</small></div><div><strong>Data completeness</strong><p>Based on non-empty cells across uploaded rows.</p></div></div><div className="quality-track"><span style={{ width: `${stats.dataQuality}%` }}></span></div><div className="quality-foot"><CheckCircle2 size={14} /> Original data preserved · No automatic deletion</div></div>
        </div>
      </>}
      <input ref={fileInput} type="file" accept=".csv,.xls,.xlsx" hidden onChange={(e) => uploadFile(e.target.files?.[0])} />
    </>
  );

  const renderInventory = () => (
    <>
      <PageHeading eyebrow="STOCK CONTROL" title="Inventory Intelligence" description="Monitor reorder requirements and possible excess stock." />
      <div className="kpi-grid"><KpiCard title="Total stock units" value={stats.totalStock.toLocaleString("en-IN")} icon={Boxes} /><KpiCard title="Low stock products" value={stats.lowStock.length} icon={AlertTriangle} alert /><KpiCard title="Possible overstock" value={stats.overstock.length} icon={Layers3} /><KpiCard title="Products analysed" value={rows.length} icon={Package} /></div>
      <div className="panel table-panel"><PanelTitle title="Reorder attention list" subtitle="Products at or below their recorded reorder level" />{stats.lowStock.length ? <DataTable rows={stats.lowStock} /> : <EmptyChart message="No low-stock records found, or stock/reorder columns are unavailable." />}</div>
      <div className="panel table-panel"><PanelTitle title="Possible overstock list" subtitle="Stock quantity greater than 3× reorder level — screening rule" />{stats.overstock.length ? <DataTable rows={stats.overstock} /> : <EmptyChart message="No possible overstock records found." />}</div>
    </>
  );

  const renderExpiry = () => (
    <>
      <PageHeading eyebrow="PRODUCT SAFETY MONITOR" title="Expiry Intelligence" description="Identify expired products and upcoming expiry dates." />
      <div className="kpi-grid">
        <KpiCard title="Expired records" value={stats.expirySummary.Expired ?? stats.expired.length} icon={ShieldAlert} alert />
        <KpiCard title="Expiring within 7 days" value={stats.expirySummary["Expiring within 7 days"] ?? stats.expiring7.length} icon={Clock3} />
        <KpiCard title="Expiring in days 8–30" value={stats.expirySummary["Expiring within 30 days"] ?? stats.expiring8to30.length} icon={Clock3} />
        <KpiCard title="Valid dates" value={stats.expirySummary.Valid ?? stats.validExpiry.length} icon={CheckCircle2} />
        <KpiCard title="Ambiguous dates" value={stats.expirySummary.Ambiguous ?? stats.ambiguousExpiry.length} icon={CircleHelp} alert={stats.ambiguousExpiry.length > 0} />
        <KpiCard title="Missing dates" value={stats.expirySummary.Missing ?? stats.missingExpiry.length} icon={Database} />
        <KpiCard title="Dataset records" value={rows.length} icon={Database} />
      </div>
      <div className="panel table-panel"><PanelTitle title="Expired products" subtitle="Records with a recognised expiry date before today" />{stats.expired.length ? <DataTable rows={stats.expired} /> : <EmptyChart message="No expired records found." />}</div>
      <div className="panel table-panel"><PanelTitle title="Upcoming expiry" subtitle="Products expiring within 30 days" />{stats.expiringSoon.length ? <DataTable rows={stats.expiringSoon} /> : <EmptyChart message="No upcoming expiry records found." />}</div>
      {stats.ambiguousExpiry.length > 0 && <div className="panel table-panel"><PanelTitle title="Ambiguous expiry dates" subtitle="These dates require review; NEXORA does not guess month/day order." /><DataTable rows={stats.ambiguousExpiry} /></div>}
      {stats.missingExpiry.length > 0 && <div className="panel table-panel"><PanelTitle title="Missing expiry dates" subtitle="Records without an expiry date value." /><DataTable rows={stats.missingExpiry} /></div>}
    </>
  );

  const renderSuppliers = () => (
    <>
      <PageHeading eyebrow="SUPPLY NETWORK" title="Supplier Intelligence" description="Understand supplier distribution in your product catalogue." />
      <div className="panel table-panel"><PanelTitle title="Supplier portfolio" subtitle="Number of product records associated with each supplier" />{stats.suppliers.length ? <div className="supplier-list">{stats.suppliers.map((supplier, i) => <div className="supplier-row" key={supplier.name}><div className="supplier-rank">0{i + 1}</div><div className="supplier-info"><strong>{supplier.name}</strong><span>Product records</span></div><div className="supplier-count">{supplier.products}</div></div>)}</div> : <EmptyChart message="Supplier information is not available in this dataset." />}</div>
    </>
  );

  const renderAI = () => (
    <>
      <PageHeading
        eyebrow="NEXORA COPILOT · 410 PATTERNS · MEMORY ON"
        title="AI Intelligence"
        description="Ask 200+ question variations. Every answer is grounded in real computations with session memory."
      />
      <div className="ai-hero">
        <div className="ai-glow"></div>
        <div className="ai-orb"><BrainCircuit size={32} /></div>
        <div className="eyebrow">DATASET-AWARE ASSISTANT</div>
        <h2>Ask your retail data <span>anything.</span></h2>
        <p>I understand 410 phrasings across stock, sales, expiry, categories, suppliers and more.</p>

        <div className="ai-input-wrap">
          <Search size={18} />
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && askCopilot()}
            placeholder="e.g. What should I reorder? · Any expiring soon? · Top products"
          />
          <button onClick={() => askCopilot()} disabled={aiLoading}>
            <Sparkles size={16} />
            {aiLoading ? "Thinking..." : "Analyse"}
          </button>
        </div>

        <div style={{ marginTop: "20px", display: "flex", justifyContent: "center" }}>
          <select
            value={questionCategory}
            onChange={(e) => setQuestionCategory(e.target.value)}
            style={{
              background: "rgba(7,14,24,.85)",
              color: "#e6d1a1",
              border: "1px solid rgba(216,189,131,.35)",
              borderRadius: "10px",
              padding: "10px 18px",
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.5px",
              cursor: "pointer",
              outline: "none",
              minWidth: "260px",
              boxShadow: "0 4px 20px rgba(216,189,131,.08)",
            }}
          >
            {Object.keys(QUESTION_CATEGORIES).map((cat) => (
              <option key={cat} value={cat} style={{ background: "#0e1827", color: "#eef0f5" }}>
                📂 {cat}
              </option>
            ))}
          </select>
        </div>

        <div className="suggestion-chips" style={{ marginTop: "12px" }}>
          {(QUESTION_CATEGORIES[questionCategory] || []).map((item) => (
            <button key={item} onClick={() => askCopilot(item)}>{item}</button>
          ))}
        </div>

        <div style={{ marginTop: "10px", fontSize: "9px", color: "#8996a8", textAlign: "center" }}>
          Showing {QUESTION_CATEGORIES[questionCategory]?.length || 0} example questions · {Object.values(QUESTION_CATEGORIES).flat().length} total across {Object.keys(QUESTION_CATEGORIES).length} categories
        </div>

        {copilotHistory.length > 0 && (
          <div style={{ marginTop: "16px", display: "flex", alignItems: "center", justifyContent: "center", gap: "12px", fontSize: "10px", color: "#8996a8" }}>
            <span>
              🧠 Memory: <strong style={{ color: "#e6d1a1" }}>{copilotHistory.length} turn(s) stored</strong>
            </span>
            <button
              onClick={clearCopilotMemory}
              style={{
                background: "transparent",
                border: "1px solid rgba(216,189,131,.3)",
                color: "#d8bd83",
                borderRadius: "6px",
                padding: "3px 8px",
                fontSize: "9px",
                cursor: "pointer",
              }}
            >
              Clear memory
            </button>
          </div>
        )}

        {answer && (
          <div className="ai-answer">
            <div className="answer-icon"><Sparkles size={17} /></div>
            <div className="ai-answer-content">
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                <strong>NEXORA Copilot</strong>
                {copilotIntent && (
                  <span
                    style={{
                      fontSize: "8px",
                      background: "rgba(216,189,131,.15)",
                      color: "#e6d1a1",
                      padding: "2px 7px",
                      borderRadius: "10px",
                      letterSpacing: "0.5px",
                      textTransform: "uppercase",
                    }}
                  >
                    {copilotIntent.replace(/_/g, " ")}
                  </span>
                )}
              </div>
              <AIAnswer answer={answer} />
            </div>
          </div>
        )}
      </div>

      <div className="section-heading">
        <div><span className="eyebrow">INSIGHT ENGINE</span><h2>Detected observations</h2></div>
      </div>
      <div className="insight-grid">
        {insights.map((item, i) => {
          const Icon = item.icon;
          return (
            <div className={`insight-card ${item.type}`} key={i}>
              <div className="insight-icon"><Icon size={19} /></div>
              <div><h3>{item.title}</h3><p>{item.detail}</p></div>
            </div>
          );
        })}
      </div>
      <div className="notice-box">
        <Zap size={17} />
        <p>
          <strong>Copilot memory active.</strong> NEXORA remembers your last 3 turns.
          Try follow-ups like "show those" or "more details". Every answer is computed
          from real data — never invented.
        </p>
      </div>
    </>
  );

  const renderSupplierScorecard = () => {
    const summary = supplierScoreData?.summary || {};
    const suppliers = supplierScoreData?.suppliers || [];
    return (
      <>
        <PageHeading eyebrow="SUPPLY NETWORK HEALTH" title="Supplier Scorecard" description="Rank suppliers by contribution and inventory health. Grades A to D." />
        <div className="kpi-grid">
          <KpiCard title="Total suppliers" value={summary.total_suppliers ?? "—"} icon={Truck} />
          <KpiCard title="Grade A" value={summary.grade_a ?? "—"} icon={CheckCircle2} />
          <KpiCard title="Grade B" value={summary.grade_b ?? "—"} icon={CircleHelp} />
          <KpiCard title="Grade C / D" value={(summary.grade_c ?? 0) + (summary.grade_d ?? 0)} icon={AlertTriangle} alert={(summary.grade_c + summary.grade_d) > 0} />
        </div>
        <div className="panel" style={{ marginTop: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Supplier ranking" subtitle="Score blends contribution (50 pts) minus inventory risk (50 pts)" />
            <button className="gold-button" onClick={loadSupplierScorecard} disabled={supplierScoreLoading || !rows.length}><RefreshCw size={14} />{supplierScoreLoading ? "Scoring..." : supplierScoreData ? "Re-score" : "Score Suppliers"}</button>
          </div>
          {suppliers.length > 0 ? (
            <div style={{ marginTop: "14px" }}>
              <DataTable rows={suppliers.map((s) => ({ Supplier: s.supplier, Grade: s.grade, Score: s.score, Products: s.product_count, "Total Value": s.total_value, "Low Stock": s.low_stock_count, "Dead Stock": s.dead_stock_count }))} />
            </div>
          ) : !supplierScoreLoading && (<EmptyChart message="Click 'Score Suppliers' to rank your suppliers." />)}
        </div>
        {supplierScoreData?.available && suppliers.length > 0 && (
          <div className="notice-box" style={{ marginTop: "20px" }}><CircleHelp size={17} /><p><strong>How grading works:</strong> Suppliers with Grade A are reliable, high-value partners. Grade C and D suppliers have high risk from low stock or dead inventory — consider renegotiating terms or diversifying.</p></div>
        )}
      </>
    );
  };

  const renderAbc = () => {
    const summary = abcData?.summary || {};
    const renderTier = (title, rows) => (
      <div className="panel"><PanelTitle title={title} subtitle={`${rows?.length || 0} products`} />
        {rows && rows.length ? <DataTable rows={rows.slice(0, 20).map((r) => ({ Product: r.product, Sales: r.sales, Revenue: r.revenue ?? "—", "Cumulative %": `${r.cumulative_pct?.toFixed(1)}%` }))} /> : <EmptyChart message="No products in this tier." />}
      </div>
    );
    return (
      <>
        <PageHeading eyebrow="PARETO INTELLIGENCE" title="ABC Analysis" description="Classify products into A/B/C tiers using cumulative sales contribution. 80% of revenue usually comes from ~20% of products." />
        <div className="panel" style={{ marginBottom: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Dead Stock Detection" subtitle="Products with stock but zero sales — money tied up in idle inventory" />
            <button className="gold-button" onClick={loadDeadStock} disabled={deadStockLoading || !rows.length}><AlertTriangle size={14} />{deadStockLoading ? "Analysing..." : deadStockData ? "Re-analyse" : "Detect Dead Stock"}</button>
          </div>
          {deadStockData?.available && (
            <div className="kpi-grid" style={{ marginTop: "14px" }}>
              <KpiCard title="Dead stock products" value={deadStockData.summary.dead_stock_count} icon={AlertTriangle} alert={deadStockData.summary.dead_stock_count > 0} />
              <KpiCard title="Dead stock units" value={deadStockData.summary.total_dead_units} icon={Boxes} />
              <KpiCard title="Value at risk" value={deadStockData.summary.has_price_data ? deadStockData.summary.total_value_at_risk : "N/A"} icon={CircleDollarSign} note={deadStockData.summary.has_price_data ? "Stock × price" : "No price column"} />
              <KpiCard title="Threshold" value={deadStockData.summary.sales_threshold} icon={Clock3} note="Sales ≤ this = dead" />
            </div>
          )}
          {deadStockData?.records?.length ? <div style={{ marginTop: "14px" }}><DataTable rows={deadStockData.records} /></div> : deadStockData?.available && deadStockData.summary.dead_stock_count === 0 ? <div className="notice-box" style={{ marginTop: "14px" }}><CheckCircle2 size={17} /><p><strong>No dead stock found.</strong> Every product with stock has recorded sales.</p></div> : null}
        </div>
        <div className="kpi-grid">
          <KpiCard title="Products analysed" value={summary.total_products ?? "—"} icon={Package} />
          <KpiCard title="Tier A (top 80%)" value={summary.a_count ?? "—"} icon={TrendingUp} />
          <KpiCard title="Tier B (next 15%)" value={summary.b_count ?? "—"} icon={Layers3} />
          <KpiCard title="Tier C (last 5%)" value={summary.c_count ?? "—"} icon={Boxes} />
        </div>
        <div className="panel" style={{ marginTop: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Run ABC classification" subtitle={abcData?.available ? `A: ${summary.a_sales_pct}% sales · B: ${summary.b_sales_pct}% · C: ${summary.c_sales_pct}%` : "Analyse your dataset to classify products"} />
            <button className="gold-button" onClick={loadAbcAnalysis} disabled={abcLoading || !rows.length}><Sparkles size={14} />{abcLoading ? "Analysing..." : abcData ? "Re-analyse" : "Run ABC Analysis"}</button>
          </div>
          {!abcData && !abcLoading && <EmptyChart message="Click 'Run ABC Analysis' to classify products by sales contribution." />}
          {abcLoading && <EmptyChart message="Analysing product contribution..." />}
          {abcData && !abcData.available && <EmptyChart message={abcData.message || "Not enough data."} />}
        </div>
        <div className="panel" style={{ marginTop: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Reorder Point Calculator" subtitle="Smart reorder suggestions based on sales velocity (7-day lead time)" />
            <button className="gold-button" onClick={loadReorderPoints} disabled={reorderLoading || !rows.length}><RefreshCw size={14} />{reorderLoading ? "Calculating..." : reorderData ? "Re-calculate" : "Calculate Reorder Points"}</button>
          </div>
          {reorderData?.available && (
            <div className="kpi-grid" style={{ marginTop: "14px" }}>
              <KpiCard title="Critical — order now" value={reorderData.summary.critical} icon={AlertTriangle} alert={reorderData.summary.critical > 0} />
              <KpiCard title="Watch — low" value={reorderData.summary.watch} icon={Clock3} />
              <KpiCard title="Healthy stock" value={reorderData.summary.healthy} icon={CheckCircle2} />
              <KpiCard title="Total order units" value={reorderData.summary.total_order_units} icon={Boxes} note={`Lead time: ${reorderData.lead_time_days} days`} />
            </div>
          )}
          {reorderData?.records?.length > 0 ? (
            <div style={{ marginTop: "14px" }}>
              <DataTable rows={reorderData.records.map((r) => ({ Product: r.product, Status: r.status, "Current Stock": r.current_stock, "Daily Sales": r.daily_sales, "Reorder Point": r.reorder_point, "Suggested Order": r.suggested_order }))} />
            </div>
          ) : reorderData && !reorderData.available ? (
            <EmptyChart message={reorderData.message || "Not enough data."} />
          ) : null}
          {!reorderData && !reorderLoading && (<EmptyChart message="Click 'Calculate Reorder Points' to see which products to order." />)}
        </div>
        <div className="panel" style={{ marginTop: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Category × Month Heatmap" subtitle="Monthly sales volume per category — spot seasonal patterns" />
            <button className="gold-button" onClick={loadHeatmap} disabled={heatmapLoading || !rows.length}><Activity size={14} />{heatmapLoading ? "Loading..." : heatmapData ? "Re-load" : "Generate Heatmap"}</button>
          </div>
          {heatmapData?.available && heatmapData.grid?.length > 0 ? (
            <div style={{ overflowX: "auto", marginTop: "16px" }}>
              <table style={{ borderCollapse: "collapse", minWidth: "100%" }}>
                <thead>
                  <tr><th style={{ textAlign: "left", padding: "8px 12px", fontSize: "9px", color: "#8f9caf" }}>Category</th>{heatmapData.months.map((m) => <th key={m} style={{ padding: "8px 12px", fontSize: "9px", color: "#8f9caf", textAlign: "center" }}>{m}</th>)}</tr>
                </thead>
                <tbody>
                  {heatmapData.grid.map((row) => (
                    <tr key={row.category}>
                      <td style={{ padding: "8px 12px", fontSize: "10px", color: "#e1e5ec", borderBottom: "1px solid rgba(190,205,225,.06)" }}>{row.category}</td>
                      {row.values.map((v, i) => {
                        const intensity = heatmapData.max_value > 0 ? v / heatmapData.max_value : 0;
                        const bg = `rgba(216,189,131,${(intensity * 0.85 + 0.05).toFixed(2)})`;
                        const color = intensity > 0.5 ? "#1a2233" : "#d4d9e2";
                        return <td key={i} style={{ padding: "10px 12px", fontSize: "10px", textAlign: "center", background: bg, color: color, borderBottom: "1px solid rgba(190,205,225,.06)", fontWeight: intensity > 0.6 ? 600 : 400 }}>{v.toLocaleString("en-IN")}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : heatmapData && !heatmapData.available ? (
            <EmptyChart message={heatmapData.message || "Not enough data for a heatmap."} />
          ) : null}
          {!heatmapData && !heatmapLoading && (<EmptyChart message="Click 'Generate Heatmap' to see category sales by month." />)}
        </div>
        {abcData?.available && (
          <>
            <div className="section-heading"><div><span className="eyebrow">CLASSIFICATION RESULT</span><h2>Product tiers</h2></div></div>
            <div className="tier-summary">
              <div className="tier-chip tier-a"><span>A</span><div><strong>{summary.a_count}</strong><small>Top 80% sales</small></div></div>
              <div className="tier-chip tier-b"><span>B</span><div><strong>{summary.b_count}</strong><small>Next 15%</small></div></div>
              <div className="tier-chip tier-c"><span>C</span><div><strong>{summary.c_count}</strong><small>Last 5%</small></div></div>
            </div>
            <div className="tier-grid">{renderTier("Tier A — High priority", abcData.a)}{renderTier("Tier B — Medium priority", abcData.b)}{renderTier("Tier C — Low priority", abcData.c)}</div>
            <div className="notice-box"><CircleHelp size={17} /><p><strong>Interpretation:</strong> Prioritise inventory and marketing for Tier A products. Tier C items can be reviewed for discontinuation or reduced ordering.</p></div>
          </>
        )}
      </>
    );
  };

  const renderWhatIf = () => (
    <>
      <PageHeading eyebrow="DECISION SIMULATOR" title="What-If Simulator" description="Simulate price and sales changes to see projected revenue impact." />
      <div className="panel">
        <div className="table-toolbar">
          <PanelTitle title="Simulation parameters" subtitle="Adjust sliders to see projected impact" />
          <button className="gold-button" onClick={loadWhatIf} disabled={whatIfLoading || !rows.length}>
            <Sparkles size={14} /> {whatIfLoading ? "Simulating..." : "Run Simulation"}
          </button>
        </div>
        <div style={{ padding: "20px 0" }}>
          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "8px", color: "#d4d9e2" }}>
              Price Change: <strong style={{ color: priceChange >= 0 ? "#58b9aa" : "#e17c83" }}>{priceChange > 0 ? "+" : ""}{priceChange}%</strong>
            </label>
            <input type="range" min="-50" max="50" value={priceChange} onChange={(e) => setPriceChange(Number(e.target.value))} style={{ width: "100%", accentColor: "#d8bd83" }} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "8px", color: "#d4d9e2" }}>
              Sales Volume Change: <strong style={{ color: salesChange >= 0 ? "#58b9aa" : "#e17c83" }}>{salesChange > 0 ? "+" : ""}{salesChange}%</strong>
            </label>
            <input type="range" min="-50" max="50" value={salesChange} onChange={(e) => setSalesChange(Number(e.target.value))} style={{ width: "100%", accentColor: "#d8bd83" }} />
          </div>
        </div>

        {whatIfData?.available && (
          <div className="kpi-grid" style={{ marginTop: "20px" }}>
            <KpiCard title="Current Revenue" value={`$${whatIfData.current.revenue.toLocaleString("en-IN")}`} icon={CircleDollarSign} />
            <KpiCard title="Projected Revenue" value={`$${whatIfData.projected.revenue.toLocaleString("en-IN")}`} icon={TrendingUp} />
            <KpiCard title="Revenue Change" value={`${whatIfData.delta.percent > 0 ? "+" : ""}${whatIfData.delta.percent}%`} icon={whatIfData.delta.revenue >= 0 ? TrendingUp : AlertTriangle} alert={whatIfData.delta.revenue < 0} />
            <KpiCard title="Projected Units" value={whatIfData.projected.units.toLocaleString("en-IN")} icon={Boxes} />
          </div>
        )}
      </div>
    </>
  );

  const renderRiskMap = () => {
    const riskItems = riskMapData?.risk_map || [];
    return (
      <>
        <PageHeading eyebrow="RISK OVERVIEW" title="Business Risk Map" description="Categories ranked by risk score (low stock, dead stock, expiring)." />
        <div className="kpi-grid">
          <KpiCard title="Categories at risk" value={riskMapData?.total_risk_categories ?? "—"} icon={AlertTriangle} alert={riskMapData?.total_risk_categories > 0} />
          <KpiCard title="Total categories" value={riskItems.length} icon={Layers3} />
        </div>
        <div className="panel" style={{ marginTop: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Risk heatmap" subtitle="Darker red = higher combined risk" />
            <button className="gold-button" onClick={loadRiskMap} disabled={riskMapLoading || !rows.length}>
              <RefreshCw size={14} /> {riskMapLoading ? "Loading..." : "Load Risk Map"}
            </button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "12px", marginTop: "16px" }}>
            {riskItems.map((item) => {
              const intensity = item.risk_score / 100;
              const bg = `rgba(225,124,131,${(intensity * 0.8 + 0.1).toFixed(2)})`;
              return (
                <div key={item.category} style={{ padding: "16px", borderRadius: "12px", border: "1px solid rgba(190,205,225,.1)", background: bg }}>
                  <strong style={{ display: "block", color: "#1a2233", fontSize: "13px", marginBottom: "10px" }}>{item.category}</strong>
                  <div style={{ fontSize: "10px", color: "#1a2233" }}>
                    <div>Low Stock: {item.low_stock}</div>
                    <div>Dead Stock: {item.dead_stock}</div>
                    <div>Expiring: {item.expiring}</div>
                  </div>
                  <div style={{ marginTop: "10px", fontWeight: 800, fontSize: "18px", color: "#1a2233" }}>Score: {item.risk_score}</div>
                </div>
              );
            })}
          </div>
        </div>
      </>
    );
  };

  const renderCalculations = () => {
    const allCals = calcList?.calculations || [];
    const filtered = calcCategory === "All"
      ? allCals
      : allCals.filter((c) => c.category === calcCategory);

    // Detect what to render — no reliance on `type` field
    const hasRecords = calcResult && Array.isArray(calcResult.records) && calcResult.records.length > 0;
    const hasValue = calcResult && calcResult.value !== undefined && calcResult.value !== null;
    const hasSummary = calcResult && calcResult.summary && typeof calcResult.summary === "object";
    const hasChart = calcResult && Array.isArray(calcResult.chart_data) && calcResult.chart_data.length > 0;

    return (
      <>
        <PageHeading
          eyebrow="MATHEMATICAL ENGINE"
          title="Calculation Library"
          description="60+ business formulas with live results from your dataset."
        />

        <div className="panel">
          <div className="table-toolbar">
            <PanelTitle
              title="Metrics registry"
              subtitle={`${allCals.length} formulas across ${calcList?.categories?.length || 0} categories`}
            />
            <button className="gold-button" onClick={loadCalculations} disabled={calcLoading}>
              <RefreshCw size={14} /> {calcLoading ? "Loading..." : calcList ? "Reload" : "Load Calculations"}
            </button>
          </div>

          {calcList && (
            <>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "16px" }}>
                <button
                  className={calcCategory === "All" ? "gold-button" : "outline-button"}
                  onClick={() => setCalcCategory("All")}
                >
                  All
                </button>
                {(calcList.categories || []).map((cat) => (
                  <button
                    key={cat}
                    className={calcCategory === cat ? "gold-button" : "outline-button"}
                    onClick={() => setCalcCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px", marginTop: "20px" }}>
                {filtered.map((calc) => (
                  <div
                    key={calc.id}
                    onClick={() => runCalculation(calc.id)}
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      background: calcSelected === calc.id ? "rgba(216,189,131,.15)" : "rgba(22,34,51,.7)",
                      border: calcSelected === calc.id ? "1px solid var(--gold)" : "1px solid var(--line)",
                      cursor: "pointer",
                      transition: ".2s",
                    }}
                  >
                    <div style={{ fontSize: "9px", color: "var(--gold)", letterSpacing: "1px", marginBottom: "6px" }}>
                      {calc.category.toUpperCase()}
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#e1e5ec", marginBottom: "8px" }}>
                      {calc.name}
                    </div>
                    <div style={{ fontSize: "10px", color: "#8996a8", fontFamily: "monospace" }}>
                      {calc.formula}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {calcResult && (
          <div className="panel" style={{ marginTop: "20px" }}>
            <PanelTitle
              title="Live Result"
              subtitle={calcResult.metric?.name ? `Computed from current dataset · ${calcResult.metric.name}` : "Computed from current dataset"}
            />

            {/* Formula */}
            {calcResult.metric?.formula && (
              <div style={{ padding: "14px", background: "rgba(216,189,131,.06)", borderRadius: "10px", marginTop: "12px" }}>
                <div style={{ fontSize: "10px", color: "#8996a8", marginBottom: "6px" }}>Formula</div>
                <div style={{ fontSize: "12px", fontFamily: "monospace", color: "#e6d1a1" }}>
                  {calcResult.metric.formula}
                </div>
              </div>
            )}

            {/* Required columns */}
            {calcResult.metric?.required && (
              <div style={{ padding: "14px", background: "rgba(88,185,170,.06)", borderRadius: "10px", marginTop: "12px" }}>
                <div style={{ fontSize: "10px", color: "#8996a8", marginBottom: "6px" }}>Required Columns</div>
                <div style={{ fontSize: "11px", color: "#58b9aa" }}>
                  {calcResult.metric.required.join(" · ")}
                </div>
              </div>
            )}

            {/* Error */}
            {calcResult.error && (
              <div className="notice-box" style={{ borderColor: "var(--red)", marginTop: "12px" }}>
                <AlertTriangle size={17} />
                <p><strong>Error:</strong> {calcResult.error}</p>
              </div>
            )}

            {/* RESULT AREA — always tries to display something */}
            {!calcResult.error && (
              <div style={{ padding: "20px", background: "rgba(255,255,255,.03)", borderRadius: "10px", marginTop: "12px" }}>
                <div style={{ fontSize: "10px", color: "#8996a8", marginBottom: "10px" }}>Result</div>

                {/* 1. Summary cards */}
                {hasSummary && (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "12px", marginBottom: hasRecords ? "20px" : 0 }}>
                    {Object.entries(calcResult.summary).map(([k, v]) => (
                      <div key={k} style={{ padding: "14px", background: "rgba(216,189,131,.08)", borderRadius: "10px", border: "1px solid rgba(216,189,131,.2)" }}>
                        <div style={{ fontSize: "9px", color: "#8996a8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "6px" }}>
                          {k.replace(/_/g, " ")}
                        </div>
                        <div style={{ fontSize: "20px", fontWeight: 800, color: "#e6d1a1" }}>
                          {typeof v === "number" ? v.toLocaleString("en-IN") : String(v ?? "—")}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 2. Chart */}
                {hasChart && (
                  <div style={{ height: "320px", marginBottom: hasRecords ? "20px" : 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      {calcResult.metric?.id === "sales_forecast" ? (
                        <LineChart data={calcResult.chart_data}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#283448" />
                          <XAxis dataKey="name" tick={{ fill: "#8996a8", fontSize: 10 }} />
                          <YAxis tick={{ fill: "#8996a8", fontSize: 10 }} />
                          <Tooltip contentStyle={{ background: "#182235", border: "1px solid #3a465a", borderRadius: 10 }} />
                          <Line type="monotone" dataKey="value" stroke="#d8bd83" strokeWidth={2} dot={{ r: 3 }} />
                        </LineChart>
                      ) : (
                        <BarChart data={calcResult.chart_data}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#283448" />
                          <XAxis dataKey="name" tick={{ fill: "#8996a8", fontSize: 10 }} />
                          <YAxis tick={{ fill: "#8996a8", fontSize: 10 }} />
                          <Tooltip contentStyle={{ background: "#182235", border: "1px solid #3a465a", borderRadius: 10 }} />
                          <Bar dataKey="value" fill="#d8bd83" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                )}

                {/* 3. Records table */}
                {hasRecords && (
                  <DataTable rows={calcResult.records} />
                )}

                {/* 4. Plain scalar value (number or string) */}
                {!hasSummary && !hasChart && !hasRecords && hasValue && (
                  <div style={{ fontSize: "32px", fontWeight: 800, color: "#e6d1a1" }}>
                    {typeof calcResult.value === "number"
                      ? calcResult.value.toLocaleString("en-IN")
                      : String(calcResult.value)}
                  </div>
                )}

                {/* 5. Fallback — nothing matched, show raw data */}
                {!hasSummary && !hasChart && !hasRecords && !hasValue && (
                  <pre style={{ fontSize: "10px", color: "#e1e5ec", whiteSpace: "pre-wrap", overflow: "auto" }}>
                    {JSON.stringify(calcResult, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}
      </>
    );
  };

  const renderReport = () => {
    const theme = reportTheme === "dark"
      ? {
          bg: "#0b111c",
          panel: "#131e2e",
          text: "#edf0f5",
          muted: "#8995a8",
          gold: "#d8bd83",
          line: "rgba(190,205,225,.15)",
          chartFill: "#d8bd83",
          chartFill2: "#58b9aa",
        }
      : {
          bg: "#ffffff",
          panel: "#f7f7f9",
          text: "#1a2233",
          muted: "#5a6478",
          gold: "#b8944d",
          line: "rgba(0,0,0,.1)",
          chartFill: "#b8944d",
          chartFill2: "#4a9087",
        };

    return (
      <>
        <PageHeading eyebrow="PROFESSIONAL REPORT" title="Business Report" description="Download a branded PDF or the fully-cleaned Excel file." />

        <div className="panel" style={{ marginBottom: "20px" }}>
          <div className="table-toolbar">
            <PanelTitle title="Export options" subtitle="Choose a theme, then download" />
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <select
                value={reportTheme}
                onChange={(e) => setReportTheme(e.target.value)}
                style={{
                  background: "#0e1827",
                  color: "#eef0f5",
                  border: "1px solid rgba(216,189,131,.3)",
                  borderRadius: "8px",
                  padding: "8px 12px",
                  fontSize: "11px",
                  cursor: "pointer",
                }}
              >
                <option value="dark">Dark / Gold theme</option>
                <option value="light">White / Print theme</option>
              </select>
              <button
                className="outline-button"
                onClick={downloadCleanedExcel}
                disabled={!rows.length}
              >
                <FileDown size={14} /> Cleaned Excel
              </button>
              <button
                className="gold-button"
                onClick={downloadPdfReport}
                disabled={pdfGenerating || !rows.length}
              >
                <FileDown size={14} /> {pdfGenerating ? "Generating PDF..." : "Download PDF"}
              </button>
            </div>
          </div>
        </div>

        {!rows.length ? (
          <EmptyChart message="Upload a dataset to generate a report." />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <div
              id="pdf-report-root"
              style={{
                background: theme.bg,
                color: theme.text,
                padding: "40px",
                borderRadius: "14px",
                minWidth: "820px",
                border: `1px solid ${theme.line}`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `2px solid ${theme.gold}`, paddingBottom: "16px", marginBottom: "28px" }}>
                <div>
                  <div style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "2px", color: theme.gold }}>NEXORA AI</div>
                  <div style={{ fontSize: "10px", color: theme.muted, letterSpacing: "2px", marginTop: "4px" }}>
                    RETAIL INTELLIGENCE REPORT
                  </div>
                </div>
                <div style={{ textAlign: "right", fontSize: "10px", color: theme.muted }}>
                  <div><strong style={{ color: theme.text }}>Dataset:</strong> {fileName}</div>
                  <div><strong style={{ color: theme.text }}>Rows:</strong> {rows.length.toLocaleString("en-IN")}</div>
                  <div><strong style={{ color: theme.text }}>Date:</strong> {new Date().toLocaleDateString("en-IN")}</div>
                </div>
              </div>

              <div style={{ fontSize: "13px", fontWeight: 700, color: theme.gold, marginBottom: "12px", letterSpacing: "1px" }}>
                KEY PERFORMANCE INDICATORS
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "30px" }}>
                {[
                  { label: "Products", value: stats.uniqueProducts.toLocaleString("en-IN") },
                  { label: "Total Stock", value: stats.totalStock.toLocaleString("en-IN") },
                  { label: "Sales Volume", value: stats.totalSales.toLocaleString("en-IN") },
                  { label: "Low Stock Alerts", value: stats.lowStock.length },
                ].map((kpi) => (
                  <div key={kpi.label} style={{ background: theme.panel, borderRadius: "10px", padding: "16px", border: `1px solid ${theme.line}` }}>
                    <div style={{ fontSize: "9px", color: theme.muted, letterSpacing: "1px", textTransform: "uppercase", marginBottom: "8px" }}>{kpi.label}</div>
                    <div style={{ fontSize: "22px", fontWeight: 800, color: theme.gold }}>{kpi.value}</div>
                  </div>
                ))}
              </div>

              <div style={{ fontSize: "13px", fontWeight: 700, color: theme.gold, marginBottom: "12px", letterSpacing: "1px" }}>
                CATEGORY PERFORMANCE
              </div>
              <div style={{ background: theme.panel, borderRadius: "10px", padding: "20px", border: `1px solid ${theme.line}`, marginBottom: "28px" }}>
                {stats.categories.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={stats.categories.slice(0, 8)} layout="vertical" margin={{ left: 12, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={theme.line} />
                      <XAxis type="number" tick={{ fill: theme.muted, fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" width={110} tick={{ fill: theme.text, fontSize: 10 }} />
                      <Bar dataKey="value" fill={theme.chartFill} radius={[0, 5, 5, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ color: theme.muted, fontSize: "11px", textAlign: "center", padding: "30px" }}>No category data available.</div>
                )}
              </div>

              <div style={{ fontSize: "13px", fontWeight: 700, color: theme.gold, marginBottom: "12px", letterSpacing: "1px" }}>
                TOP SELLING PRODUCTS
              </div>
              <div style={{ background: theme.panel, borderRadius: "10px", padding: "20px", border: `1px solid ${theme.line}`, marginBottom: "28px" }}>
                {stats.topProducts.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={stats.topProducts.slice(0, 8)} layout="vertical" margin={{ left: 12, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={theme.line} />
                      <XAxis type="number" tick={{ fill: theme.muted, fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" width={110} tick={{ fill: theme.text, fontSize: 10 }} />
                      <Bar dataKey="sales" fill={theme.chartFill2} radius={[0, 5, 5, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ color: theme.muted, fontSize: "11px", textAlign: "center", padding: "30px" }}>No sales data available.</div>
                )}
              </div>

              <div style={{ fontSize: "13px", fontWeight: 700, color: theme.gold, marginBottom: "12px", letterSpacing: "1px" }}>
                LOW STOCK ATTENTION
              </div>
              <div style={{ background: theme.panel, borderRadius: "10px", padding: "20px", border: `1px solid ${theme.line}`, marginBottom: "28px" }}>
                {stats.lowStock.length > 0 ? (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "10px" }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${theme.line}` }}>
                        <th style={{ textAlign: "left", padding: "8px", color: theme.muted }}>Product</th>
                        <th style={{ textAlign: "right", padding: "8px", color: theme.muted }}>Stock</th>
                        <th style={{ textAlign: "right", padding: "8px", color: theme.muted }}>Reorder Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.lowStock.slice(0, 10).map((item, i) => {
                        const productCol = stats.productCol;
                        const stockCol = stats.stockCol;
                        const reorderCol = stats.reorderCol;
                        return (
                          <tr key={i} style={{ borderBottom: `1px solid ${theme.line}` }}>
                            <td style={{ padding: "8px", color: theme.text }}>{String(item[productCol] ?? "—")}</td>
                            <td style={{ padding: "8px", textAlign: "right", color: theme.text }}>{Number(item[stockCol] || 0).toLocaleString("en-IN")}</td>
                            <td style={{ padding: "8px", textAlign: "right", color: theme.muted }}>{Number(item[reorderCol] || 0).toLocaleString("en-IN")}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div style={{ color: theme.muted, fontSize: "11px", textAlign: "center", padding: "20px" }}>No low-stock items.</div>
                )}
              </div>

              <div style={{ fontSize: "13px", fontWeight: 700, color: theme.gold, marginBottom: "12px", letterSpacing: "1px" }}>
                EXPIRY OVERVIEW
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginBottom: "28px" }}>
                <div style={{ background: theme.panel, borderRadius: "10px", padding: "16px", border: `1px solid ${theme.line}`, textAlign: "center" }}>
                  <div style={{ fontSize: "9px", color: theme.muted, letterSpacing: "1px", marginBottom: "6px" }}>EXPIRED</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#e17c83" }}>{stats.expirySummary.Expired ?? stats.expired.length}</div>
                </div>
                <div style={{ background: theme.panel, borderRadius: "10px", padding: "16px", border: `1px solid ${theme.line}`, textAlign: "center" }}>
                  <div style={{ fontSize: "9px", color: theme.muted, letterSpacing: "1px", marginBottom: "6px" }}>≤ 7 DAYS</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#e8b86e" }}>{stats.expirySummary["Expiring within 7 days"] ?? stats.expiring7.length}</div>
                </div>
                <div style={{ background: theme.panel, borderRadius: "10px", padding: "16px", border: `1px solid ${theme.line}`, textAlign: "center" }}>
                  <div style={{ fontSize: "9px", color: theme.muted, letterSpacing: "1px", marginBottom: "6px" }}>≤ 30 DAYS</div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: theme.gold }}>{stats.expirySummary["Expiring within 30 days"] ?? stats.expiring8to30.length}</div>
                </div>
              </div>

              <div style={{ fontSize: "13px", fontWeight: 700, color: theme.gold, marginBottom: "12px", letterSpacing: "1px" }}>
                AI RECOMMENDATIONS
              </div>
              <div style={{ background: theme.panel, borderRadius: "10px", padding: "20px", border: `1px solid ${theme.line}` }}>
                {insights.length > 0 ? (
                  insights.map((item, i) => (
                    <div key={i} style={{ display: "flex", gap: "10px", marginBottom: "12px", fontSize: "11px", lineHeight: 1.6 }}>
                      <span style={{ color: theme.gold, fontWeight: 700, minWidth: "20px" }}>{i + 1}.</span>
                      <div>
                        <strong style={{ color: theme.text }}>{item.title}:</strong>{" "}
                        <span style={{ color: theme.muted }}>{item.detail}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ color: theme.muted, fontSize: "11px" }}>No recommendations.</div>
                )}
              </div>

              <div style={{ marginTop: "30px", paddingTop: "16px", borderTop: `1px solid ${theme.line}`, display: "flex", justifyContent: "space-between", fontSize: "9px", color: theme.muted }}>
                <div>NEXORA AI · Smart Retail Intelligence</div>
                <div>Generated {new Date().toLocaleString("en-IN")}</div>
              </div>
            </div>
          </div>
        )}
      </>
    );
  };

  const renderStory = () => (
    <>
      <PageHeading eyebrow="AI NARRATIVE" title="Data Storytelling" description="Automated narrative explaining your current business state." />
      <div className="panel" style={{ marginTop: "20px" }}>
        <div className="table-toolbar">
          <PanelTitle title="Business summary" subtitle="Generated from live dataset metrics" />
          <button className="gold-button" onClick={loadStory} disabled={storyLoading || !rows.length}>
            <Sparkles size={14} /> {storyLoading ? "Writing..." : "Generate Story"}
          </button>
        </div>
        {storyData?.available ? (
          <div style={{ padding: "24px", background: "rgba(216,189,131,.06)", borderRadius: "12px", border: "1px solid rgba(216,189,131,.2)", marginTop: "16px", lineHeight: "1.8", fontSize: "14px", color: "#e1e5ec" }}>
            {storyData.story}
          </div>
        ) : !storyLoading && (
          <EmptyChart message="Click 'Generate Story' to read your business narrative." />
        )}
      </div>
    </>
  );

  const renderDataCleaning = () => (
    <>
      <PageHeading eyebrow="DATA HYGIENE" title="Smart Data Cleaning" description="Detect issues, review suggestions, and download a cleaned copy. Your original file is never modified." />
      <div className="kpi-grid">
        <KpiCard title="Records loaded" value={rows.length} icon={Database} />
        <KpiCard title="Issues detected" value={cleanReport?.total_issues ?? "—"} icon={AlertTriangle} />
        <KpiCard title="Fixes selected" value={Object.values(cleanSelected).filter(Boolean).length} icon={CheckCircle2} />
        <KpiCard title="Rows after clean" value={cleanResult?.cleaned_rows ?? "—"} icon={Layers3} />
      </div>
      <div className="panel">
        <div className="table-toolbar">
          <PanelTitle title="Cleaning analysis" subtitle="Detected issues and suggested fixes" />
          <div style={{ display: "flex", gap: "10px" }}>
            <button className="outline-button" onClick={analyzeCleaning} disabled={cleanLoading || !rows.length}><RefreshCw size={14} /> {cleanLoading ? "Analysing..." : "Re-analyse"}</button>
            <button className="gold-button" onClick={applyCleaning} disabled={cleanLoading || !cleanReport}><Sparkles size={14} /> Apply selected fixes</button>
          </div>
        </div>
        {!cleanReport && !cleanLoading && <EmptyChart message="Click 'Re-analyse' to inspect the dataset for issues." />}
        {cleanLoading && <EmptyChart message="Analysing the dataset..." />}
        {cleanReport && (cleanReport.issues || []).length === 0 && <div className="notice-box"><CheckCircle2 size={17} /><p><strong>No issues found.</strong> Your dataset looks clean.</p></div>}
        {cleanReport && (cleanReport.issues || []).length > 0 && (
          <div className="clean-issues">
            {cleanReport.issues.map((issue) => (
              <label className={`clean-issue ${issue.severity} ${!issue.fixable ? "not-fixable" : ""}`} key={issue.id}>
                <input type="checkbox" checked={!!cleanSelected[issue.id]} disabled={!issue.fixable || cleanLoading} onChange={(e) => setCleanSelected({ ...cleanSelected, [issue.id]: e.target.checked })} />
                <div><strong>{issue.title}</strong><p>{issue.detail}</p></div>
                {!issue.fixable && <span className="clean-badge">Manual review</span>}
              </label>
            ))}
          </div>
        )}
      </div>
      {cleanResult && (
        <div className="panel" style={{ marginTop: "20px" }}>
          <PanelTitle title="Cleaned preview" subtitle={`${cleanResult.original_rows} → ${cleanResult.cleaned_rows} rows · ${cleanResult.applied?.length || 0} fix(es) applied`} />
          <div style={{ marginBottom: "12px" }}><button className="gold-button" onClick={downloadCleaned}><FileDown size={14} /> Download cleaned CSV</button></div>
          <DataTable rows={cleanResult.preview} />
        </div>
      )}
      <div className="notice-box"><ShieldAlert size={17} /><p><strong>Original data preserved.</strong> NEXORA never overwrites your uploaded dataset. The cleaned copy is only downloaded when you click the button above.</p></div>
    </>
  );

  const renderDataStudio = () => (
    <>
      <PageHeading eyebrow="DATA MANAGEMENT" title="Data Studio" description="Explore your uploaded records and inspect data completeness." />
      <div className="kpi-grid">
        <KpiCard title="Total records" value={rows.length} icon={Database} />
        <KpiCard title="Columns detected" value={rows.length ? Object.keys(rows[0]).length : 0} icon={Layers3} />
        <KpiCard title="Completeness" value={`${stats.dataQuality}%`} icon={CheckCircle2} />
        <KpiCard title="Unique products" value={stats.uniqueProducts} icon={Package} />
      </div>
      <div className="panel table-panel">
        <div className="table-toolbar"><PanelTitle title="Dataset explorer" subtitle="Search through your uploaded records" /><div className="table-search"><Search size={15} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search records..." /></div></div>
        {rows.length ? <DataTable rows={filteredRows} /> : <EmptyChart message="Upload a dataset to explore its records." />}
      </div>
      {rows.length > 0 && (
        <div className="panel table-panel" style={{ marginTop: "20px" }}>
          <PanelTitle title="Column validation" subtitle="Blank cells and values that could not be interpreted by supported business fields" />
          <DataTable rows={stats.columnQuality.map((item) => ({ Column: item.column, "Missing values": item.missing, "Invalid values": item.invalid, "Ambiguous dates": item.ambiguousDates }))} />
        </div>
      )}
      <div className="notice-box"><ShieldAlert size={17} /><p><strong>Data protection:</strong> NEXORA does not overwrite your original file. Ambiguous date formats are not silently interpreted. Review and clean data intentionally before operational decisions.</p></div>
    </>
  );

  const renderSales = () => (
    <>
      <PageHeading eyebrow="COMMERCIAL PERFORMANCE" title="Sales Intelligence" description="Explore the sales measures available in your uploaded dataset." />
      <div className="kpi-grid">
        <KpiCard title="Recorded sales volume" value={stats.totalSales.toLocaleString("en-IN")} icon={TrendingUp} />
        <KpiCard title="Products tracked" value={stats.uniqueProducts} icon={Package} />
        <KpiCard title="Categories found" value={stats.categories.length} icon={Layers3} />
        <KpiCard title="Estimated sales value" value={unknownCurrencyValue(stats.estimatedSalesValue)} note={stats.currency} icon={CircleDollarSign} />
        <KpiCard title="Inventory value" value={unknownCurrencyValue(stats.inventoryValue)} note={stats.currency} icon={Boxes} />
      </div>
      <div className="panel table-panel"><PanelTitle title="Top selling products" subtitle="Ranked by recorded sales volume" />{stats.topProducts.length ? <DataTable rows={stats.topProducts.map((item) => ({ Product: item.name, Sales_Volume: item.sales }))} /> : <EmptyChart message="A product name and sales volume column are required." />}</div>
      <div className="notice-box"><CircleHelp size={17} /><p><strong>Forecasting note:</strong> Received/order dates are not automatically treated as transaction dates. Reliable sales forecasting needs dated sales transactions or a suitable time series.</p></div>
    </>
  );

  const pageContent = () => {
    if (activePage === "Overview") return renderOverview();
    if (activePage === "Sales Intelligence") return renderSales();
    if (activePage === "Inventory") return renderInventory();
    if (activePage === "Expiry Monitor") return renderExpiry();
    if (activePage === "Suppliers") return renderSuppliers();
    if (activePage === "ABC Analysis") return renderAbc();
    if (activePage === "Supplier Scorecard") return renderSupplierScorecard();
    if (activePage === "AI Intelligence") return renderAI();
    if (activePage === "Data Cleaning") return renderDataCleaning();
    if (activePage === "Data Studio") return renderDataStudio();
    if (activePage === "What-If Simulator") return renderWhatIf();
    if (activePage === "Business Risk Map") return renderRiskMap();
    if (activePage === "Data Storytelling") return renderStory();
    if (activePage === "Business Report") return renderReport();
    if (activePage === "Calculations") return renderCalculations();
    return renderOverview();
  };
  if (!isAuthenticated) {
    return renderLogin();
  }

  return (
    <div className="nexora-app">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand"><div className="brand-mark"><span>N</span><i></i></div><div><strong>NEXORA</strong><small>INTELLIGENCE SYSTEM</small></div><button className="mobile-close" onClick={() => setSidebarOpen(false)}><X size={19} /></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-card"><div className="workspace-icon"><Activity size={17} /></div><div><strong>Retail Command</strong><span>Intelligence workspace</span></div><span className="workspace-dot"></span></div>
        <div className="nav-label">MAIN MENU</div>
        <nav className="navigation">
          {NAVIGATION.map(({ label, icon: Icon }) => (
            <button key={label} className={`nav-item ${activePage === label ? "active" : ""}`} onClick={() => { setActivePage(label); setSidebarOpen(false); }}>
              <Icon size={18} /><span>{label}</span>{activePage === label && <i />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-card"><div className="system-icon"><Sparkles size={16} /></div><strong>Intelligence mode</strong><p>Insights generated from your uploaded dataset.</p><span><i></i> SYSTEM READY</span></div>
          <button className="nav-item settings-item" onClick={() => setActivePage("Data Studio")}><Settings size={18} /> Settings & data</button>
          <div className="sidebar-version">NEXORA AI <span>v1.0</span></div>
        </div>
      </aside>
      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left"><button className="mobile-menu" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button><div className="breadcrumb">Workspace <ChevronRight size={13} /> <strong>{activePage}</strong></div></div>
                    <div className="topbar-right">
            <div className={`topbar-status ${backendStatus === "Backend connected" ? "backend-connected" : "backend-offline"}`}>
              <span></span>{backendStatus}
            </div>
            <button className="top-icon" title="Notifications"><Bell size={18} /><i /></button>
            <div className="profile-avatar">N</div>
            <button className="logout-btn" onClick={handleLogout} title="Log out">Log out</button>
          </div>
        </header>
        <div className="page-content">
          {pageContent()}
          <footer className="footer">
            <div><span className="footer-mark">N</span> NEXORA AI <span className="footer-muted">· Smart Retail Intelligence</span></div>
            <span>Built for better retail decisions.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function KpiCard({ title, value, icon: Icon, note, alert }) {
  return <div className={`kpi-card ${alert ? "kpi-alert" : ""}`}><div className="kpi-top"><span>{title}</span><div className="kpi-icon"><Icon size={18} /></div></div><div className="kpi-value">{value}</div><div className="kpi-note"><span className="kpi-dot"></span>{note || "Calculated from uploaded data"}</div></div>;
}

function PanelTitle({ title, subtitle }) {
  return <div className="panel-title"><div><h3>{title}</h3><p>{subtitle}</p></div><span className="panel-menu">•••</span></div>;
}

function PageHeading({ eyebrow, title, description }) {
  return <div className="welcome-row"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p className="subtitle">{description}</p></div></div>;
}

function EmptyChart({ message }) {
  return <div className="empty-chart"><div><ScanSearch size={23} /></div><p>{message}</p></div>;
}

function AIAnswer({ answer }) {
  if (typeof answer === "string") return <p>{answer}</p>;
  if (!answer || typeof answer !== "object") return null;
  return (
    <>
      <p>{answer.answer || "No answer text was returned."}</p>
      {answer.insights?.length > 0 && <div className="answer-insights">{answer.insights.map((item, index) => <div className="answer-insight" key={`${item.label}-${index}`}><span>{item.label}</span><strong>{Number(item.value).toLocaleString("en-IN")}</strong></div>)}</div>}
      {answer.chart?.data?.length > 0 && <div className="answer-chart"><ResponsiveContainer width="100%" height={220}><BarChart data={answer.chart.data}><CartesianGrid strokeDasharray="3 3" stroke="#283448" /><XAxis dataKey="label" tick={{ fill: "#aab5c4", fontSize: 10 }} /><YAxis tick={{ fill: "#aab5c4", fontSize: 10 }} /><Tooltip /><Bar dataKey="value" fill="#d8bd83" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>}
      {answer.records?.length > 0 && <div className="answer-records"><PanelTitle title="Source records" subtitle={`${answer.records.length.toLocaleString("en-IN")} verified records`} /><DataTable rows={answer.records} />{answer.records.length >= 100 && <span className="table-footer">Showing first 100 source records for this answer.</span>}</div>}
    </>
  );
}

function DataTable({ rows }) {
  if (!rows?.length) return <EmptyChart message="No records available." />;
  return <PaginatedTable rows={rows} />;
}

function PaginatedTable({ rows }) {
  const [page, setPage] = useState(0);
  const pageSize = 25;
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  useEffect(() => setPage(0), [rows.length]);
  const columns = Object.keys(rows[0]);
  const visibleRows = rows.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>{columns.map((column) => <th key={column}>{column.replace(/_/g, " ")}</th>)}</tr>
          </thead>
          <tbody>
            {visibleRows.map((row, i) => (
              <tr key={page * pageSize + i}>
                {columns.map((column) => <td key={column}>{String(row[column] ?? "—")}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > pageSize && (
        <div className="pagination-bar">
          <span>Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, rows.length)} of {rows.length}</span>
          <div>
            <button type="button" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0}>Previous</button>
            <span>Page {page + 1} of {pageCount}</span>
            <button type="button" onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} disabled={page >= pageCount - 1}>Next</button>
          </div>
        </div>
      )}
    </>
  );
}

export default App;