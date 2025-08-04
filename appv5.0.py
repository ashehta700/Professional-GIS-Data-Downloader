"""
Professional GIS Data Downloader v5.0
=====================================
Streamlined, high-performance GIS data extraction tool
Features:
- Clean, intuitive interface
- Multiple data sources (Microsoft Buildings, OSM, Natural Earth)
- Flexible AOI selection (draw or upload shapefile)
- Individual and bulk downloads
- Real-time data preview
- Professional export formats
"""

import os
import time
import zipfile
import tempfile
import json
from io import BytesIO
from datetime import datetime
from typing import List, Tuple, Dict, Any

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import shape, Point
from shapely.ops import unary_union
import mercantile
import requests
import osmnx as ox

# ================================================================
# PAGE CONFIGURATION
# ================================================================
st.set_page_config(
    page_title="GIS Data Downloader v5.0",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: .5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    .data-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    .status-success { 
        background: #10b981; color: white; padding: 0.5rem 1rem; 
        border-radius: 8px; display: inline-block; margin: 0.25rem 0; 
    }
    .status-warning { 
        background: #f59e0b; color: white; padding: 0.5rem 1rem; 
        border-radius: 8px; display: inline-block; margin: 0.25rem 0; 
    }
    .download-table {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# ================================================================
# SESSION STATE INITIALIZATION
# ================================================================
if 'aoi_geometry' not in st.session_state:
    st.session_state.aoi_geometry = None
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = {}
if 'selected_layers' not in st.session_state:
    st.session_state.selected_layers = []

# ================================================================
# DATA SOURCE CONFIGURATIONS
# ================================================================
DATA_SOURCES = {
    "Microsoft Buildings": {
        "description": "High-quality building footprints worldwide",
        "icon": "🏢",
        "color": "#FF6B6B"
    },
    "OpenStreetMap Roads": {
        "description": "Road networks from OpenStreetMap",
        "icon": "🛣️",
        "color": "#4ECDC4",
        "osm_tags": {"highway": True}
    },
    "OpenStreetMap Buildings": {
        "description": "Building footprints from OpenStreetMap",
        "icon": "🏗️",
        "color": "#45B7D1",
        "osm_tags": {"building": True}
    },
    "OpenStreetMap Waterways": {
        "description": "Rivers, streams, and water features",
        "icon": "🌊",
        "color": "#96CEB4",
        "osm_tags": {"waterway": True}
    },
    "OpenStreetMap Parks": {
        "description": "Parks and recreational areas",
        "icon": "🌳",
        "color": "#FFEAA7",
        "osm_tags": {"leisure": ["park", "garden", "recreation_ground"]}
    },
    "OpenStreetMap Amenities": {
        "description": "Points of interest and amenities",
        "icon": "📍",
        "color": "#DDA0DD",
        "osm_tags": {"amenity": True}
    },
    "Natural Earth Countries": {
        "description": "Country boundaries (Natural Earth)",
        "icon": "🗺️",
        "color": "#98D8C8"
    }
}

# ================================================================
# UTILITY FUNCTIONS
# ================================================================
@st.cache_data(ttl=3600)
def load_microsoft_buildings_index():
    """Load Microsoft Buildings dataset index"""
    try:
        url = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
        return pd.read_csv(url, dtype=str)
    except Exception as e:
        st.error(f"Failed to load Microsoft Buildings index: {e}")
        return pd.DataFrame()

def create_base_map(center=[24.7136, 46.6753], zoom=10):
    """Create base map with drawing tools"""
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")
    
    # Add drawing tools
    Draw(
        export=True,
        draw_options={
            "polygon": True,
            "rectangle": True,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "polyline": False
        }
    ).add_to(m)
    
    return m

def process_uploaded_shapefile(uploaded_file):
    """Process uploaded shapefile and extract geometry"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        # Extract and read shapefile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            
            # Find .shp file
            shp_files = [f for f in os.listdir(tmp_dir) if f.endswith('.shp')]
            if not shp_files:
                raise ValueError("No .shp file found in the uploaded ZIP")
            
            shp_path = os.path.join(tmp_dir, shp_files[0])
            gdf = gpd.read_file(shp_path)
            
            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            # Union all geometries to create single AOI
            aoi_geometry = unary_union(gdf.geometry.values)
            
        os.unlink(tmp_path)
        return aoi_geometry
        
    except Exception as e:
        st.error(f"Error processing shapefile: {e}")
        return None

# ================================================================
# DATA FETCHING FUNCTIONS
# ================================================================
def fetch_microsoft_buildings(aoi_geometry):
    """Fetch Microsoft Buildings data for AOI"""
    try:
        # Get tile quadkeys for AOI
        minx, miny, maxx, maxy = aoi_geometry.bounds
        tiles = list(mercantile.tiles(minx, miny, maxx, maxy, zooms=9))
        quad_keys = [mercantile.quadkey(t) for t in tiles]
        
        if not quad_keys:
            return gpd.GeoDataFrame()
        
        # Load index
        df_index = load_microsoft_buildings_index()
        if df_index.empty:
            return gpd.GeoDataFrame()
        
        # Fetch data
        all_buildings = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, qk in enumerate(quad_keys[:10]):  # Limit to first 10 tiles for performance
            status_text.text(f"Fetching tile {i+1}/{min(len(quad_keys), 10)}")
            
            tile_data = df_index[df_index["QuadKey"] == qk]
            if not tile_data.empty:
                url = tile_data.iloc[0]["Url"]
                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        # Parse GeoJSON lines
                        for line in response.text.strip().split('\n'):
                            if line:
                                feature = json.loads(line)
                                geom = shape(feature['geometry'])
                                if geom.intersects(aoi_geometry):
                                    all_buildings.append({
                                        'geometry': geom,
                                        'source': 'Microsoft Buildings',
                                        'tile_id': qk
                                    })
                except Exception as e:
                    continue
            
            progress_bar.progress((i + 1) / min(len(quad_keys), 10))
        
        progress_bar.empty()
        status_text.empty()
        
        if all_buildings:
            return gpd.GeoDataFrame(all_buildings, crs='EPSG:4326')
        else:
            return gpd.GeoDataFrame()
            
    except Exception as e:
        st.error(f"Error fetching Microsoft Buildings: {e}")
        return gpd.GeoDataFrame()

def fetch_osm_data(aoi_geometry, tags):
    """Fetch OSM data for AOI"""
    try:
        with st.spinner("Fetching OSM data..."):
            gdf = ox.features_from_polygon(aoi_geometry, tags=tags)
            
            if not gdf.empty:
                # Clean and simplify data
                gdf = gdf.reset_index()
                # Keep only essential columns
                essential_cols = ['geometry', 'name', 'highway', 'building', 'amenity', 'waterway', 'leisure']
                available_cols = [col for col in essential_cols if col in gdf.columns]
                if len(available_cols) > 1:  # Keep geometry + at least one other column
                    gdf = gdf[available_cols]
                
            return gdf
            
    except Exception as e:
        st.error(f"Error fetching OSM data: {e}")
        return gpd.GeoDataFrame()

def fetch_natural_earth_countries(aoi_geometry):
    """Fetch Natural Earth countries data (placeholder)"""
    try:
        # In a real implementation, you would fetch from Natural Earth
        # This is a placeholder that creates a simple point
        center = aoi_geometry.centroid
        return gpd.GeoDataFrame({
            'name': ['Sample Country'],
            'geometry': [center]
        }, crs='EPSG:4326')
    except Exception as e:
        st.error(f"Error fetching Natural Earth data: {e}")
        return gpd.GeoDataFrame()

# ================================================================
# EXPORT FUNCTIONS
# ================================================================
def export_layer_data(gdf, layer_name, format_type):
    """Export layer data in specified format"""
    if gdf.empty:
        return None
    
    safe_name = layer_name.lower().replace(' ', '_').replace('/', '_')
    
    try:
        if format_type == "GeoJSON":
            data = gdf.to_json().encode('utf-8')
            filename = f"{safe_name}.geojson"
            mime = "application/geo+json"
            
        elif format_type == "CSV":
            # Export without geometry
            df_no_geom = gdf.drop(columns='geometry') if 'geometry' in gdf.columns else gdf
            data = df_no_geom.to_csv(index=False).encode('utf-8')
            filename = f"{safe_name}.csv"
            mime = "text/csv"
            
        elif format_type == "Shapefile":
            # Create shapefile ZIP
            with tempfile.TemporaryDirectory() as tmp_dir:
                shp_path = os.path.join(tmp_dir, f"{safe_name}.shp")
                gdf.to_file(shp_path, driver="ESRI Shapefile")
                
                # Create ZIP with all shapefile components
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file in os.listdir(tmp_dir):
                        if file.startswith(safe_name):
                            zf.write(os.path.join(tmp_dir, file), file)
                
                data = zip_buffer.getvalue()
                filename = f"{safe_name}_shapefile.zip"
                mime = "application/zip"
                
        else:
            return None
            
        return {"data": data, "filename": filename, "mime": mime}
        
    except Exception as e:
        st.error(f"Export error for {layer_name}: {e}")
        return None

def create_bulk_download(selected_data, export_format):
    """Create bulk download ZIP file"""
    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            
            # Add metadata
            metadata = {
                "export_date": datetime.now().isoformat(),
                "layers": list(selected_data.keys()),
                "format": export_format,
                "total_features": sum(len(gdf) for gdf in selected_data.values())
            }
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Add each layer
            for layer_name, gdf in selected_data.items():
                export_result = export_layer_data(gdf, layer_name, export_format)
                if export_result:
                    zf.writestr(export_result["filename"], export_result["data"])
        
        return zip_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Bulk download error: {e}")
        return None

# ================================================================
# MAIN APPLICATION
# ================================================================

# Header
st.markdown("""
<div class="main-header">
    <h1>🌍 GIS Data Downloader APP</h1>
    <p>Professional geospatial data extraction From Any Opensource </p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Data Source Selection
with st.sidebar:
    st.markdown("## 📊 Data Sources")
    st.markdown("Select the layers you want to download:")
    
    selected_sources = []
    for source_name, config in DATA_SOURCES.items():
        if st.checkbox(f"{config['icon']} {source_name}", key=source_name):
            selected_sources.append(source_name)
    
    st.markdown("---")
    
    # Export format selection
    st.markdown("## 📁 Export Format")
    export_format = st.selectbox(
        "Choose export format:",
        ["GeoJSON", "CSV", "Shapefile"]
    )
    
    st.markdown("---")
    
    # AOI Upload option
    st.markdown("## 📂 Upload AOI")
    uploaded_shapefile = st.file_uploader(
        "Upload Shapefile (ZIP)",
        type="zip",
        help="Upload a ZIP file containing shapefile components"
    )

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🗺️ Area of Interest Selection")
    
    # Process uploaded shapefile
    if uploaded_shapefile and st.session_state.aoi_geometry is None:
        aoi_from_file = process_uploaded_shapefile(uploaded_shapefile)
        if aoi_from_file:
            st.session_state.aoi_geometry = aoi_from_file
            st.success("✅ Shapefile uploaded successfully!")
    
    # Create and display map
    base_map = create_base_map()
    
    # Add existing AOI to map
    if st.session_state.aoi_geometry:
        folium.GeoJson(
            st.session_state.aoi_geometry.__geo_interface__,
            style_function=lambda x: {
                'fillColor': 'blue',
                'color': 'blue',
                'weight': 2,
                'fillOpacity': 0.1
            }
        ).add_to(base_map)
    
    # Add loaded data to map
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
    for i, (layer_name, gdf) in enumerate(st.session_state.loaded_data.items()):
        if not gdf.empty:
            color = colors[i % len(colors)]
            folium.GeoJson(
                gdf,
                name=layer_name,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 2,
                    'fillOpacity': 0.3
                }
            ).add_to(base_map)
    
    if st.session_state.loaded_data:
        folium.LayerControl().add_to(base_map)
    
    # Display map
    map_data = st_folium(base_map, height=500, width="100%", returned_objects=["last_active_drawing"])

with col2:
    st.markdown("### 🎛️ Control Panel")
    
    # AOI Status
    if st.session_state.aoi_geometry:
        st.markdown('<div class="status-success">✅ AOI Selected</div>', unsafe_allow_html=True)
        # Calculate approximate area
        bounds = st.session_state.aoi_geometry.bounds
        area_km2 = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) * 111 * 111
        st.metric("Approx. Area", f"{area_km2:.1f} km²")
    else:
        st.markdown('<div class="status-warning">⚠️ No AOI Selected</div>', unsafe_allow_html=True)
        st.info("Draw a polygon on the map or upload a shapefile")
    
    # Data loading
    st.markdown("#### 📥 Data Loading")
    
    if selected_sources and st.session_state.aoi_geometry:
        if st.button("🚀 Fetch Selected Data", type="primary", use_container_width=True):
            st.session_state.loaded_data = {}
            
            for source_name in selected_sources:
                with st.spinner(f"Loading {source_name}..."):
                    if source_name == "Microsoft Buildings":
                        gdf = fetch_microsoft_buildings(st.session_state.aoi_geometry)
                    elif source_name.startswith("OpenStreetMap"):
                        config = DATA_SOURCES[source_name]
                        if "osm_tags" in config:
                            gdf = fetch_osm_data(st.session_state.aoi_geometry, config["osm_tags"])
                        else:
                            gdf = gpd.GeoDataFrame()
                    elif source_name == "Natural Earth Countries":
                        gdf = fetch_natural_earth_countries(st.session_state.aoi_geometry)
                    else:
                        gdf = gpd.GeoDataFrame()
                    
                    if not gdf.empty:
                        st.session_state.loaded_data[source_name] = gdf
                        st.success(f"✅ {source_name}: {len(gdf)} features")
                    else:
                        st.warning(f"⚠️ {source_name}: No data found")
            
            st.rerun()
    else:
        if not selected_sources:
            st.info("Select data sources from the sidebar")
        if not st.session_state.aoi_geometry:
            st.info("Define an area of interest first")
    
    # Clear data
    if st.session_state.loaded_data:
        if st.button("🗑️ Clear All Data", use_container_width=True):
            st.session_state.loaded_data = {}
            st.rerun()

# Process map interactions
if map_data and map_data.get("last_active_drawing"):
    new_aoi = shape(map_data["last_active_drawing"]["geometry"])
    if not st.session_state.aoi_geometry or not new_aoi.equals_exact(st.session_state.aoi_geometry, tolerance=1e-6):
        st.session_state.aoi_geometry = new_aoi
        st.rerun()

# Data preview and download section
if st.session_state.loaded_data:
    st.markdown("---")
    st.markdown("## 📊 Data Preview & Downloads")
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    total_features = sum(len(gdf) for gdf in st.session_state.loaded_data.values())
    
    with col1:
        st.metric("Total Layers", len(st.session_state.loaded_data))
    with col2:
        st.metric("Total Features", f"{total_features:,}")
    with col3:
        st.metric("Export Format", export_format)
    
    # Download table
    st.markdown("### 📥 Download Center")
    
    download_data = []
    for layer_name, gdf in st.session_state.loaded_data.items():
        download_data.append({
            "Layer": layer_name,
            "Features": f"{len(gdf):,}",
            "Geometry": ", ".join(gdf.geometry.geom_type.unique()),
            "Select": False
        })
    
    if download_data:
        # Create download table
        download_df = pd.DataFrame(download_data)
        
        # Layer selection for bulk download
        st.markdown("#### Select layers for bulk download:")
        selected_for_bulk = []
        
        for i, row in download_df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
            
            with col1:
                selected = st.checkbox("", key=f"bulk_{i}")
                if selected:
                    selected_for_bulk.append(row["Layer"])
            
            with col2:
                st.write(f"{DATA_SOURCES[row['Layer']]['icon']} **{row['Layer']}**")
            
            with col3:
                st.write(row["Features"])
            
            with col4:
                st.write(row["Geometry"])
            
            with col5:
                # Individual download button
                layer_gdf = st.session_state.loaded_data[row["Layer"]]
                export_result = export_layer_data(layer_gdf, row["Layer"], export_format)
                if export_result:
                    st.download_button(
                        "📥 Download",
                        data=export_result["data"],
                        file_name=export_result["filename"],
                        mime=export_result["mime"],
                        key=f"download_{i}",
                        use_container_width=True
                    )
        
        # Bulk download section
        if selected_for_bulk:
            st.markdown("---")
            st.markdown(f"#### 📦 Bulk Download ({len(selected_for_bulk)} layers selected)")
            
            selected_data = {name: st.session_state.loaded_data[name] for name in selected_for_bulk}
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.info(f"Selected: {', '.join(selected_for_bulk)}")
            
            with col2:
                bulk_data = create_bulk_download(selected_data, export_format)
                if bulk_data:
                    st.download_button(
                        "📦 Download Selected Layers",
                        data=bulk_data,
                        file_name=f"gis_bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
        
        # Data preview
        st.markdown("### 👁️ Data Preview")
        preview_layer = st.selectbox("Select layer to preview:", list(st.session_state.loaded_data.keys()))
        
        if preview_layer:
            preview_gdf = st.session_state.loaded_data[preview_layer]
            if not preview_gdf.empty:
                # Show first 10 rows without geometry
                preview_df = preview_gdf.drop(columns='geometry').head(10)
                st.dataframe(preview_df, use_container_width=True)
                
                # Layer statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Features", len(preview_gdf))
                with col2:
                    st.metric("Attributes", len(preview_gdf.columns) - 1)
                with col3:
                    st.metric("CRS", str(preview_gdf.crs))

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 1rem; background: rgb(115 82 173); border-radius: 8px;">
    <p><strong>🌍 GIS Data Downloader v5.0</strong> | Built with ❤️ by Ahmed Shehta</p>
    <p><small>Powered by Streamlit, Folium, GeoPandas , Microsoft Model & OSMnx</small></p>
</div>
""", unsafe_allow_html=True)