# 🛒 E-Commerce Business Intelligence

An end-to-end e-commerce analytics project built using Python, Pandas, and Plotly to analyze sales performance, profitability, product categories, and regional trends.

## 📌 Project Overview

This project transforms raw e-commerce data into actionable business insights through data cleaning, dimensional modeling, business analysis, and an interactive dashboard.

## 🛠️ Tech Stack

- Python
- Pandas
- SQL concepts and dimensional modeling
- HTML and CSS
- JavaScript
- Plotly
- Git and GitHub

## 🔄 Project Workflow

1. Raw Data Collection
2. Data Cleaning and Validation
3. Data Transformation using Pandas
4. Star Schema Construction
5. Business Analysis
6. Interactive Dashboard Development
7. Business Insights and Recommendations

## 📊 Dashboard Features

- Total Revenue
- Total Profit
- Profit Margin
- Unique Orders
- Monthly Revenue and Profit Trends
- Revenue by Product Category
- Profit Margin by Category
- Revenue by Region
- Top 10 Products by Revenue
- Interactive Year, Region, and Category Filters
- Data Quality Indicators

## 📈 Key Results

| Metric | Result |
|---|---:|
| Order Records | 25,000 |
| Total Revenue | ₹29,495,186 |
| Total Profit | ₹6,758,974 |
| Profit Margin | 22.92% |
| Unique Orders | 25,000 |

## 🔍 Initial Business Insights

- Home & Kitchen generated the highest category revenue.
- Furniture recorded the highest category profit margin.
- North generated the highest regional revenue.
- Data quality checks identified invalid dates and missing dimension keys.

## 🗂️ Project Structure

```text
AI_Ecommerce_Analytics/
├── Data/
│   ├── fact_orders.csv
│   ├── dim_customer.csv
│   ├── dim_product.csv
│   ├── dim_region.csv
│   └── dim_date.csv
├── clean_customers.py
├── clean_products.py
├── clean_orders.py
├── clean_regions.py
├── create_date_dimension.py
├── build_star_schema.py
├── business_analysis.py
├── dashboard.py
├── index.html
└── README.md