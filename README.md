# 🌍 GIS Data Downloader v5.0

A professional, open-source geospatial data extraction application built with **Streamlit**, **Folium**, **GeoPandas**, **OSMnx**, and **Microsoft Building Footprints**.

![App Screenshot](https://your-screenshot-url-here.png) <!-- Optional: Replace with a real image or GIF -->

## 📦 Overview

**GIS Data Downloader v5.0** is a streamlined, high-performance web application that enables users to select an area of interest (AOI) and download GIS data from various authoritative open data sources in professional formats. It's tailored for researchers, urban planners, geospatial analysts, and developers who need flexible access to clean, structured geospatial data.

---

## 🚀 Features

- 🧭 **Interactive AOI Selection**: Draw polygons directly on the map or upload a shapefile.
- 🗂️ **Multiple Open Data Sources**:
  - 🏢 Microsoft Building Footprints
  - 🛣️ OpenStreetMap Roads
  - 🏗️ OpenStreetMap Buildings
  - 🌊 OpenStreetMap Waterways
  - 🌳 OpenStreetMap Parks
  - 📍 OpenStreetMap Amenities
  - 🗺️ Natural Earth Countries
- 📥 **Data Export Formats**: GeoJSON, Shapefile, and CSV
- 🎯 **Real-time Map Preview** and statistics
- 📦 **Bulk and Individual Layer Downloads**
- 📊 **Layer Summary** and feature type display

---

## 🗺️ Supported Data Layers

| Source                | Description                                   |
|-----------------------|-----------------------------------------------|
| 🏢 **Microsoft Buildings** | High-resolution global building footprints |
| 🛣️ **OSM Roads**         | Road networks (highway, residential, etc.)   |
| 🏗️ **OSM Buildings**     | Building outlines via OSM                    |
| 🌊 **OSM Waterways**     | Rivers, canals, and streams                  |
| 🌳 **OSM Parks**         | Parks, gardens, and recreational areas      |
| 📍 **OSM Amenities**     | Points of interest (schools, hospitals, etc.)|
| 🗺️ **Natural Earth**     | Country boundaries (low resolution)         |

---

## 📽️ How to Use

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ashehta700/Professional-GIS-Data-Downloader.git
   cd Professional-GIS-Data-Downloader
   ```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```
3. **Run the app**:
```bash
streamlit run app.py
```
4. **Use the interface**:
   - Select data layers
   - Choose export format
   - Define AOI by drawing or uploading shapefile
   - Fetch data and download it
   📂 Export Formats
   - GeoJSON: Ideal for web applications and modern GIS tools
   - Shapefile (ZIP): Widely supported legacy format
   - CSV: Tabular data excluding geometry, great for reporting
   📹 Demo Video
   - Watch the full walkthrough here: YouTube Video
   
   
## 📜 License
## This project is licensed under the MIT License — feel free to use and modify it freely.

## 🙌 Credits
## Developed with ❤️ by Ahmed Shehta 
https://ahmed-shehta.netlify.app
