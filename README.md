# 🏙️ El Paso Rental Market Dashboard

[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-2563eb?style=for-the-badge&logo=github)](https://hoffmanap.github.io/rentcast_ep/)
[![Data Source](https://img.shields.io/badge/Data-RentCast.io-16a34a?style=for-the-badge)](https://rentcast.io)

Welcome to the **El Paso Rental Market Dashboard**! This project tracks, aggregates, and visualizes residential rental trends across El Paso, Texas, providing insights into spatial distribution and pricing changes over time.

## 📊 Live Dashboard
**Explore the interactive data here:** 👉 [https://hoffmanap.github.io/rentcast_ep/](https://hoffmanap.github.io/rentcast_ep/)

---

## ✨ Features
* **Interactive Spatial Map:** A grayscale interactive map displaying the most recent rental listings, color-coded and sized dynamically based on price metrics.
* **Time Series Analysis:** Track the citywide average rent against specific property sizes (1, 2, 3, and 4+ bedrooms).
* **Dynamic Zip Code Tracking:** Compare specific neighborhoods by toggling El Paso zip codes on and off to see localized historical trends.
* **Metric Toggling:** Switch seamlessly between raw **Monthly Rent ($)** and **Price per Square Foot ($)** to get a true sense of market value.

---

## 🗄️ Data Source
All rental property data powering this dashboard is proudly sourced from **[RentCast.io](https://rentcast.io/)**. 

Data is aggregated on a weekly basis and appended directly to the repository's historical dataset (`rent_history.csv`). 

---

## 🛠️ Architecture & Tech Stack
This project runs entirely client-side and is hosted via **GitHub Pages**, meaning it requires zero backend server maintenance. As the automated weekly script updates the CSV, the front-end dashboard automatically parses and visualizes the latest data on page load. 

**Powered By:**
* **HTML/CSS/Vanilla JS** - Core structure and styling
* **PapaParse** - Fast, in-browser CSV processing
* **Leaflet.js** - Interactive mapping (using CartoDB basemaps)
* **Chart.js** - Responsive time-series data visualization

## 🏘️ Related: AMI & Development Feasibility Analysis

A deeper analysis of this data lives in [`ami-feasibility/`](./ami-feasibility) — comparing
market rents to HUD income limits and to what it actually costs to build or convert middle
housing in El Paso.

**Live page:** https://hoffmanap.github.io/rentcast_ep/ami-feasibility/

---
