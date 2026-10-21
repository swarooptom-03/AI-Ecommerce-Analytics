import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "Data"
OUTPUT_FILE = BASE_DIR / "index.html"

# 1. Load data
fact = pd.read_csv(DATA_DIR / "fact_orders.csv")
products = pd.read_csv(DATA_DIR / "dim_product.csv")
regions = pd.read_csv(DATA_DIR / "dim_region.csv")

fact["order_date_parsed"] = pd.to_datetime(
    fact["order_date_parsed"], errors="coerce"
)

for col in ["sales_amount", "profit"]:
    fact[col] = pd.to_numeric(fact[col], errors="coerce")

# 2. Join dimensions
df = fact.merge(
    products[["product_key", "product_name", "category"]],
    on="product_key",
    how="left",
    validate="many_to_one",
).merge(
    regions[["region_key", "region"]],
    on="region_key",
    how="left",
    validate="many_to_one",
)

df["category"] = df["category"].fillna("Unknown / Unassigned")
df["region"] = df["region"].fillna("Unknown / Unassigned")
df["product_name"] = df["product_name"].fillna("Unknown product")
df["year"] = df["order_date_parsed"].dt.year.astype("Int64").astype(str)
df.loc[df["order_date_parsed"].isna(), "year"] = "Invalid date"
df["month"] = df["order_date_parsed"].dt.to_period("M").astype(str)

# 3. Prepare data for the interactive dashboard
records_df = df[
    [
        "order_id",
        "year",
        "month",
        "region",
        "category",
        "product_name",
        "sales_amount",
        "profit",
    ]
].copy()

records_df = records_df.astype(object).where(
    pd.notna(records_df), None
)

payload = json.dumps(
    records_df.to_dict(orient="records"),
    ensure_ascii=False,
    allow_nan=False,
)

quality = {
    "invalid_dates": int(df["order_date_parsed"].isna().sum()),
    "missing_customers": int(fact["customer_key"].isna().sum()),
    "missing_products": int(fact["product_key"].isna().sum()),
    "missing_regions": int(fact["region_key"].isna().sum()),
}

# 4. Dashboard HTML
html = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>E-Commerce Business Intelligence</title>
<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>

<style>
:root {
    --bg: #f3f6fb;
    --white: #ffffff;
    --ink: #17243a;
    --muted: #718096;
    --line: #e4eaf2;
    --blue: #356df3;
    --teal: #0d9488;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
}

.container { max-width: 1600px; margin: auto; padding: 26px; }

.hero {
    padding: 32px;
    border-radius: 20px;
    color: white;
    background: linear-gradient(115deg, #14243d, #1e4677 65%, #356df3);
    box-shadow: 0 5px 22px rgba(24,43,74,.06);
}

.eyebrow {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #c2d5ff;
    margin-bottom: 12px;
}

h1 { margin: 0 0 10px; font-size: clamp(27px,3vw,38px); }
.subtitle { max-width: 760px; color: #dce7f8; font-size: 14px; line-height: 1.7; }

.badges { display: flex; gap: 9px; flex-wrap: wrap; margin-top: 20px; }
.badge {
    padding: 7px 12px;
    border-radius: 30px;
    font-size: 11px;
    background: rgba(255,255,255,.1);
    border: 1px solid rgba(255,255,255,.17);
}

.section-heading { margin: 28px 2px 14px; }
.section-heading h2 { margin: 0; font-size: 17px; }
.section-heading p { margin: 6px 0 0; color: var(--muted); font-size: 12px; }

.filters {
    display: grid;
    grid-template-columns: repeat(3,minmax(0,1fr));
    gap: 16px;
    padding: 19px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 16px;
}

label {
    display: block;
    margin-bottom: 9px;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--muted);
}

select {
    width: 100%;
    padding: 12px;
    border: 1px solid #dce3ee;
    border-radius: 9px;
    background: #fbfcff;
    color: var(--ink);
    font-size: 13px;
}

.kpis {
    display: grid;
    grid-template-columns: repeat(4,minmax(0,1fr));
    gap: 15px;
    margin-top: 15px;
}

.kpi {
    padding: 20px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 16px;
    min-width: 0;
}

.kpi-label { color: var(--muted); font-size: 12px; }
.kpi-value { margin-top: 14px; font-size: clamp(21px,2vw,29px); font-weight: 800; overflow-wrap: anywhere; }
.kpi-note { margin-top: 8px; color: var(--muted); font-size: 11px; }
.kpi-line { height: 4px; margin-top: 17px; border-radius: 10px; background: var(--blue); }
.kpi:nth-child(2) .kpi-line { background: var(--teal); }
.kpi:nth-child(3) .kpi-line { background: #8b65df; }
.kpi:nth-child(4) .kpi-line { background: #e99a35; }

.chart-grid {
    display: grid;
    grid-template-columns: repeat(2,minmax(0,1fr));
    gap: 16px;
}

.panel {
    min-width: 0;
    padding: 21px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 17px;
    box-shadow: 0 5px 22px rgba(24,43,74,.04);
}

.panel h3 { margin: 0; font-size: 14px; }
.panel-description { margin-top: 6px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.chart { width: 100%; height: 350px; margin-top: 8px; }
.chart.products { height: 400px; }

.insights {
    display: grid;
    grid-template-columns: repeat(3,minmax(0,1fr));
    gap: 15px;
}

.insight {
    padding: 20px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 16px;
}

.insight-tag { color: var(--blue); font-size: 10px; font-weight: 800; text-transform: uppercase; }
.insight h3 { margin: 10px 0 8px; font-size: 14px; }
.insight p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.7; }

.quality {
    margin-top: 16px;
    padding: 22px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 17px;
}

.quality h2 { margin: 0 0 8px; font-size: 15px; }
.quality-description { color: var(--muted); font-size: 12px; line-height: 1.7; }

.quality-grid {
    display: grid;
    grid-template-columns: repeat(4,minmax(0,1fr));
    gap: 11px;
}

.quality-item { padding: 15px; background: #f7f9fc; border: 1px solid var(--line); border-radius: 12px; }
.quality-item strong { display: block; margin-bottom: 5px; font-size: 22px; }
.quality-item span { color: var(--muted); font-size: 11px; }

footer { padding: 24px 8px; text-align: center; color: var(--muted); font-size: 11px; line-height: 1.7; }

@media(max-width:950px) {
    .container { padding: 16px; }
    .kpis { grid-template-columns: repeat(2,minmax(0,1fr)); }
    .chart-grid { grid-template-columns: 1fr; }
    .insights { grid-template-columns: 1fr; }
}

@media(max-width:560px) {
    .container { padding: 10px; }
    .hero { padding: 23px 19px; }
    .filters { grid-template-columns: 1fr; padding: 14px; }
    .kpi { padding: 14px; }
    .panel { padding: 14px; }
    .quality-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
    .chart { height: 310px; }
    .chart.products { height: 350px; }
}
</style>
</head>

<body>
<div class="container">

<header class="hero">
    <div class="eyebrow">Analytics & Operations</div>
    <h1>E-Commerce Business Intelligence</h1>
    <div class="subtitle">
        Explore sales performance, profitability, product categories,
        and regional trends using a cleaned dataset and dimensional model.
    </div>
    <div class="badges">
        <span class="badge">25,000 order records</span>
        <span class="badge">2024–2025</span>
        <span class="badge">Python · Pandas · Plotly</span>
    </div>
</header>

<div class="section-heading">
    <h2>Explore performance</h2>
    <p>Change the filters to update the KPIs and charts.</p>
</div>

<section class="filters">
    <div><label for="yearFilter">Order year</label><select id="yearFilter"><option value="All">All years</option></select></div>
    <div><label for="regionFilter">Region</label><select id="regionFilter"><option value="All">All regions</option></select></div>
    <div><label for="categoryFilter">Product category</label><select id="categoryFilter"><option value="All">All categories</option></select></div>
</section>

<section class="kpis">
    <article class="kpi"><div class="kpi-label">Total revenue</div><div class="kpi-value" id="revenue">—</div><div class="kpi-note">Net sales recorded</div><div class="kpi-line"></div></article>
    <article class="kpi"><div class="kpi-label">Total profit</div><div class="kpi-value" id="profit">—</div><div class="kpi-note">Includes recorded returns</div><div class="kpi-line"></div></article>
    <article class="kpi"><div class="kpi-label">Profit margin</div><div class="kpi-value" id="margin">—</div><div class="kpi-note">Profit divided by revenue</div><div class="kpi-line"></div></article>
    <article class="kpi"><div class="kpi-label">Unique orders</div><div class="kpi-value" id="orders">—</div><div class="kpi-note">Distinct order IDs</div><div class="kpi-line"></div></article>
</section>

<div class="section-heading"><h2>Performance overview</h2><p>Trends and comparisons across products, categories and regions.</p></div>

<section class="chart-grid">
    <article class="panel"><h3>Revenue & profit over time</h3><div class="panel-description">Monthly totals · invalid dates excluded</div><div id="monthlyChart" class="chart"></div></article>
    <article class="panel"><h3>Revenue by product category</h3><div class="panel-description">Hover to inspect revenue, profit and margin</div><div id="categoryChart" class="chart"></div></article>
    <article class="panel"><h3>Profit margin by category</h3><div class="panel-description">Compare profitability independently of sales volume</div><div id="marginChart" class="chart"></div></article>
    <article class="panel"><h3>Revenue by region</h3><div class="panel-description">Compare sales across regional markets</div><div id="regionChart" class="chart"></div></article>
    <article class="panel"><h3>Top 10 products by revenue</h3><div class="panel-description">Full product names with revenue and profit on hover</div><div id="productChart" class="chart products"></div></article>
</section>

<div class="section-heading"><h2>Business takeaways</h2><p>Initial findings from the full dataset.</p></div>

<section class="insights">
    <article class="insight"><div class="insight-tag">Category</div><h3>Home & Kitchen leads revenue</h3><p>Home & Kitchen generated the highest category revenue. Furniture had the highest category profit margin in the initial analysis.</p></article>
    <article class="insight"><div class="insight-tag">Region</div><h3>North leads total sales and profit</h3><p>North recorded the highest revenue and profit totals. Central had fewer orders, so compare per-order metrics before judging performance.</p></article>
    <article class="insight"><div class="insight-tag">Product</div><h3>Review product profitability</h3><p>Paper Product 94 generated comparatively low profit relative to its revenue among the top products. Review discounts and unit economics before changing prices.</p></article>
</section>

<section class="quality">
    <h2>Data quality & interpretation</h2>
    <p class="quality-description">Records with known data-quality issues were retained rather than silently deleted.</p>
    <div class="quality-grid">
        <div class="quality-item"><strong id="invalidDates">—</strong><span>Orders with invalid dates</span></div>
        <div class="quality-item"><strong id="missingCustomers">—</strong><span>Missing customer keys</span></div>
        <div class="quality-item"><strong id="missingProducts">—</strong><span>Missing product keys</span></div>
        <div class="quality-item"><strong id="missingRegions">—</strong><span>Missing region keys</span></div>
    </div>
    <p class="quality-description">Overall totals include all retained rows and recorded returns. Monthly charts exclude invalid dates. Orders with missing product IDs are grouped as Unknown / Unassigned. An internet connection is required to load Plotly charts.</p>
</section>

<footer>E-Commerce Business Intelligence · Portfolio analytics project<br>Python · Pandas · HTML · CSS · JavaScript · Plotly</footer>
</div>

<script>
const data = __PAYLOAD__;
const quality = __QUALITY__;

const money = n => "₹" + Number(n || 0).toLocaleString("en-IN",{maximumFractionDigits:0});
const fmt = n => Number(n || 0).toLocaleString("en-IN");

function uniqueValues(key) {
    return [...new Set(data.map(row => row[key] ?? "Unknown / Unassigned"))]
        .sort((a,b) => String(a).localeCompare(String(b)));
}

function fillSelect(id, values) {
    const select = document.getElementById(id);
    values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });
}

fillSelect("yearFilter", uniqueValues("year"));
fillSelect("regionFilter", uniqueValues("region"));
fillSelect("categoryFilter", uniqueValues("category"));

document.getElementById("invalidDates").textContent = fmt(quality.invalid_dates);
document.getElementById("missingCustomers").textContent = fmt(quality.missing_customers);
document.getElementById("missingProducts").textContent = fmt(quality.missing_products);
document.getElementById("missingRegions").textContent = fmt(quality.missing_regions);

const baseLayout = {
    autosize:true,
    paper_bgcolor:"rgba(0,0,0,0)",
    plot_bgcolor:"rgba(0,0,0,0)",
    font:{family:'-apple-system, BlinkMacSystemFont, "Segoe UI", Arial',size:11,color:"#718096"},
    margin:{l:60,r:20,t:15,b:60},
    xaxis:{gridcolor:"#edf1f7",automargin:true},
    yaxis:{gridcolor:"#edf1f7",automargin:true},
    legend:{orientation:"h",y:1.12,x:0},
    hoverlabel:{bgcolor:"#152641",font:{color:"#ffffff"}}
};

const chartConfig = {
    responsive:true,
    displaylogo:false,
    modeBarButtonsToRemove:["lasso2d","select2d"]
};

function getFilteredRows() {
    const year = document.getElementById("yearFilter").value;
    const region = document.getElementById("regionFilter").value;
    const category = document.getElementById("categoryFilter").value;

    return data.filter(row =>
        (year === "All" || row.year === year) &&
        (region === "All" || row.region === region) &&
        (category === "All" || row.category === category)
    );
}

function updateDashboard() {
    const rows = getFilteredRows();

    const revenue = rows.reduce((s,r) => s + Number(r.sales_amount || 0), 0);
    const profit = rows.reduce((s,r) => s + Number(r.profit || 0), 0);

    document.getElementById("revenue").textContent = money(revenue);
    document.getElementById("profit").textContent = money(profit);
    document.getElementById("margin").textContent =
        (revenue ? profit / revenue * 100 : 0).toFixed(2) + "%";
    document.getElementById("orders").textContent =
        fmt(new Set(rows.map(r => r.order_id)).size);

    // Monthly revenue and profit
    const monthly = {};

    rows.filter(r => r.month && r.month !== "NaT").forEach(r => {
        if (!monthly[r.month]) monthly[r.month] = {revenue:0, profit:0};
        monthly[r.month].revenue += Number(r.sales_amount || 0);
        monthly[r.month].profit += Number(r.profit || 0);
    });

    const months = Object.keys(monthly).sort();

    Plotly.react("monthlyChart",[
        {type:"scatter",mode:"lines",name:"Revenue",x:months,
         y:months.map(m=>monthly[m].revenue),
         line:{color:"#356df3",width:3},
         hovertemplate:"%{x}<br>Revenue: ₹%{y:,.0f}<extra></extra>"},
        {type:"scatter",mode:"lines",name:"Profit",x:months,
         y:months.map(m=>monthly[m].profit),
         line:{color:"#0d9488",width:3},
         hovertemplate:"%{x}<br>Profit: ₹%{y:,.0f}<extra></extra>"}
    ],{...baseLayout,margin:{l:70,r:15,t:15,b:55},
       yaxis:{...baseLayout.yaxis,tickformat:"~s"}},chartConfig);

    // Category totals
    const categories = {};

    rows.forEach(r => {
        if (!categories[r.category]) categories[r.category] = {revenue:0,profit:0};
        categories[r.category].revenue += Number(r.sales_amount || 0);
        categories[r.category].profit += Number(r.profit || 0);
    });

    const names = Object.keys(categories).sort(
        (a,b) => categories[b].revenue - categories[a].revenue
    );

    Plotly.newPlot("categoryChart",[{
        type:"bar",
        x:names,
        y:names.map(n=>categories[n].revenue),
        marker:{
            color:names.map(n=>categories[n].profit/Math.max(1,categories[n].revenue)*100),
            colorscale:[[0,"#b8cafa"],[1,"#356df3"]],
            showscale:false
        },
        customdata:names.map(n=>[
            categories[n].profit,
            categories[n].profit/Math.max(1,categories[n].revenue)*100
        ]),
        hovertemplate:"<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<br>Profit: ₹%{customdata[0]:,.0f}<br>Margin: %{customdata[1]:.2f}%<extra></extra>"
    }],{...baseLayout,margin:{l:55,r:15,t:15,b:85},
       xaxis:{type:"category",gridcolor:"#edf1f7",automargin:true,tickangle:-25},
       yaxis:{...baseLayout.yaxis,tickformat:"~s"}},chartConfig);

    // Profit margin by category
    const margins = names.map(n => ({
        name:n,
        revenue:categories[n].revenue,
        profit:categories[n].profit,
        margin:categories[n].revenue !== 0
            ? categories[n].profit / categories[n].revenue * 100
            : null
    })).filter(x => x.margin !== null)
      .sort((a,b) => b.margin-a.margin);

    Plotly.newPlot("marginChart",[{
        type:"bar",
        orientation:"h",
        y:margins.map(x=>x.name),
        x:margins.map(x=>x.margin),
        marker:{
            color:margins.map(x=>x.margin),
            colorscale:[[0,"#b8cafa"],[1,"#0d9488"]],
            showscale:false
        },
        customdata:margins.map(x=>[x.revenue,x.profit]),
        hovertemplate:"<b>%{y}</b><br>Profit margin: %{x:.2f}%<br>Revenue: ₹%{customdata[0]:,.0f}<br>Profit: ₹%{customdata[1]:,.0f}<extra></extra>"
    }],{...baseLayout,margin:{l:165,r:25,t:15,b:45},
       xaxis:{type:"linear",gridcolor:"#edf1f7",ticksuffix:"%",title:"Profit margin"},
       yaxis:{...baseLayout.yaxis,autorange:"reversed",automargin:true}},chartConfig);

    // Regional revenue
    const regions = {};
    rows.forEach(r => {
        regions[r.region] = (regions[r.region] || 0) + Number(r.sales_amount || 0);
    });

    const regionNames = Object.keys(regions).sort((a,b)=>regions[b]-regions[a]);
    const palette = ["#356df3","#4d7ff5","#7096f7","#91adfa","#b2c6fc"];

    Plotly.newPlot("regionChart",[{
        type:"bar",
        x:regionNames,
        y:regionNames.map(n=>regions[n]),
        marker:{color:regionNames.map((_,i)=>palette[Math.min(i,palette.length-1)])},
        hovertemplate:"<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>"
    }],{...baseLayout,margin:{l:60,r:20,t:15,b:60},
       xaxis:{type:"category",gridcolor:"#edf1f7",automargin:true},
       yaxis:{...baseLayout.yaxis,tickformat:"~s"}},chartConfig);

    // Top 10 products with complete labels
    const productTotals = {};

    rows.forEach(r => {
        const name = r.product_name || "Unknown product";
        if (!productTotals[name]) productTotals[name] = {revenue:0,profit:0};
        productTotals[name].revenue += Number(r.sales_amount || 0);
        productTotals[name].profit += Number(r.profit || 0);
    });

    const top = Object.entries(productTotals)
        .sort((a,b)=>b[1].revenue-a[1].revenue)
        .slice(0,10)
        .reverse();

    Plotly.newPlot("productChart",[{
        type:"bar",
        orientation:"h",
        y:top.map(x=>x[0]),
        x:top.map(x=>x[1].revenue),
        marker:{
            color:top.map(x=>x[1].profit),
            colorscale:[[0,"#b8cafa"],[1,"#356df3"]],
            showscale:false
        },
        customdata:top.map(x=>x[1].profit),
        hovertemplate:"<b>%{y}</b><br>Revenue: ₹%{x:,.0f}<br>Profit: ₹%{customdata:,.0f}<extra></extra>"
    }],{...baseLayout,margin:{l:180,r:20,t:12,b:45},
       yaxis:{...baseLayout.yaxis,autorange:"reversed",automargin:true},
       xaxis:{type:"linear",tickmode:"auto",tickformat:".3s",exponentformat:"none",showexponent:"none",gridcolor:"#edf1f7",automargin:true}},chartConfig);
}

["yearFilter","regionFilter","categoryFilter"].forEach(id => {
    document.getElementById(id).addEventListener("change",updateDashboard);
});

try {
    updateDashboard();
} catch (error) {
    console.error("Dashboard rendering failed:", error);
}

window.addEventListener("resize",() => {
    ["monthlyChart","categoryChart","marginChart","regionChart","productChart"]
        .forEach(id => Plotly.Plots.resize(id));
});
</script>
</body>
</html>'''

html = html.replace("__PAYLOAD__", payload)
html = html.replace("__QUALITY__", json.dumps(quality))

OUTPUT_FILE.write_text(html, encoding="utf-8")

print(f"Dashboard created successfully: {OUTPUT_FILE}")
print(f"Records included: {len(records_df):,}")
print("Refresh index.html in Chrome with Command + R.")