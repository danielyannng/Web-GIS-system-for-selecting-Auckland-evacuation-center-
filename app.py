"""
Emergency Evacuation Center Location Decision Support System 
"""

import streamlit as st
import pandas as pd
import numpy as np  # Add numpy import
import folium
from streamlit_folium import st_folium
import sys
import os
import hashlib  # Add hashlib import

# Add component path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

try:
    from src.utils.geoserver_manager import GeoServerManager, WMSLayerConfig
    from src.components.decision_analyzer import MCDAAnalyzer, SiteEvaluator, PopulationCoverageAnalyzer, RiskAssessmentAnalyzer
    from src.components.decision_map import DecisionSupportMap
    from src.utils.data_generator import (
        manage_session_state, setup_cache_controls,
        list_available_facility_files, load_specific_facility_data
    )
    # Import new Leaflet WMS components
    try:
        from src.components.leaflet_wms import (
            create_leaflet_wms_viewer_with_controls, 
            create_leaflet_background_layer_selector,
            LeafletWMSViewer
        )
        LEAFLET_WMS_AVAILABLE = True
    except ImportError as e:
        print(f"Leaflet WMS component import failed: {e}")
        LEAFLET_WMS_AVAILABLE = False
    
    GEOSERVER_AVAILABLE = True
    DECISION_TOOLS_AVAILABLE = True
except ImportError as e:
    GEOSERVER_AVAILABLE = False
    DECISION_TOOLS_AVAILABLE = False
    LEAFLET_WMS_AVAILABLE = False
    print(f"Import error: {e}")

# Page config
st.set_page_config(
    page_title="Evacuation Center Siting System",
    page_icon="🏥",
    layout="wide"
)

def main():
    """Main application function"""
    
    st.title("🏥 Emergency Evacuation Center Location Decision Support System")
    st.write("Emergency Evacuation Center Location Decision Support System")
    
    # Manage session state
    manage_session_state()
    
    # Set cache controls (call only once in main)
    setup_cache_controls()
    
    # Initialize GeoServer connection
    geoserver_manager = None
    if GEOSERVER_AVAILABLE:
        try:
            geoserver_manager = GeoServerManager("http://localhost:8080/geoserver", "admin", "geoserver")
            if geoserver_manager.test_connection():
                st.success("✅ GeoServer connected successfully!")
            else:
                st.warning("⚠️ GeoServer offline mode")
                geoserver_manager = None
        except:
            st.warning("⚠️ GeoServer offline mode")
            geoserver_manager = None
    
    # Extended tabs (Coverage analysis tab removed)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "🎯 Site Evaluation", "🗺️ Decision Map", "🌐 WMS Layers", "📁 Data Management"
    ])
    
    with tab1:
        project_overview()
    
    with tab2:
        if DECISION_TOOLS_AVAILABLE:
            site_evaluation_view(geoserver_manager)
        else:
            st.error("Decision analysis tools unavailable, please check component import")
    
    with tab3:
        if DECISION_TOOLS_AVAILABLE:
            decision_map_view(geoserver_manager)
        else:
            basic_map_view()
    
    with tab4:
        wms_layers_view(geoserver_manager)
    
    with tab5:
        data_management_view()
    
    # Global sidebar
    with st.sidebar:
        st.markdown("## 🎛️ System Console")
        
        # System status
        st.markdown("### 📡 System Status")
        if GEOSERVER_AVAILABLE and geoserver_manager:
            st.success("🟢 GeoServer Connected")
        else:
            st.error("🔴 GeoServer Offline")
        
        if DECISION_TOOLS_AVAILABLE:
            st.success("🟢 Decision Tools Available")
        else:
            st.error("🔴 Decision Tools Unavailable")
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Reset All Data", key="sidebar_reset_data"):
            # Clear data in session state
            keys_to_clear = ['sites_data', 'coverage_data', 'sites_data_for_evaluation', 'evaluated_sites_for_view', 'uploaded_data']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        
        # System settings
        st.markdown("### ⚙️ System Settings")
        
        # Auckland region boundary
        st.markdown("**Study Area Boundary**")
        st.text("Latitude: -37.0 to -36.3")
        st.text("Longitude: 174.0 to 175.5")
        
        # Default parameters
        st.markdown("**Default Parameters**")
        st.text("Service Radius: 5.0 km")
        st.text("Population Weight: 0.25")
        st.text("Risk Weight: 0.15")
        
        st.markdown("---")
        
        # About info
        with st.expander("ℹ️ About System"):
            st.markdown("""
            **Emergency Evacuation Center Location Decision Support System**
            
            Hanwen Yang & Zhanlun Zhang
            """)

def project_overview():
    """Project Overview"""
    st.markdown("## 📋 Project Overview")
    
    st.markdown("""
    ### 🎯 System Functions
    This is a GIS-based emergency evacuation center siting decision support system, integrating Multi-Criteria Decision Analysis (MCDA) methods to provide scientific site selection and evaluation tools for emergency management.
    
    ### 🔧 Main Features
    - **Multi-Criteria Decision Analysis**: Considers multiple factors such as population density, accessibility, risk level, etc.
    - **Interactive Map Visualization**: Dynamic map display based on Folium and GeoServer
    - **Site Evaluation**: Supports comprehensive evaluation and ranking of candidate sites
    - **Flexible Weight Configuration**: Users can customize the importance weights of each evaluation criterion
    """)
    
    # System status indicators
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Study Area", "Auckland", help="Auckland Region, New Zealand")
    
    with col2:
        # Check GeoServer connection status
        if GEOSERVER_AVAILABLE:
            try:
                geoserver_manager = GeoServerManager("http://localhost:8080/geoserver", "admin", "geoserver")
                if geoserver_manager.test_connection():
                    layers = geoserver_manager.get_all_layers_in_workspace("evacuation_workspace")
                    layer_count = len(layers) if layers else 0
                else:
                    layer_count = "Offline"
            except:
                layer_count = "Offline"
        else:
            layer_count = "Unavailable"
        st.metric("Data Layers", layer_count, help="Number of available geographic data layers in GeoServer")
    
    with col3:
        st.metric("Analysis Method", "MCDA", help="Multi-Criteria Decision Analysis")
    
    with col4:
        tools_status = "Available" if DECISION_TOOLS_AVAILABLE else "Unavailable"
        st.metric("Decision Tools", tools_status, help="Site evaluation and analysis tool status")
    
    # Technical architecture
    with st.expander("🏗️ Technical Architecture", expanded=False):
        st.markdown("""
        **Frontend Framework**: Streamlit  
        **Map Visualization**: leaflet + OpenStreetMap  
        **Spatial Data Service**: GeoServer WMS/WFS  
        **Analysis Algorithm**: Multi-Criteria Decision Analysis (MCDA)  
        **Data Formats**: Shapefile, CSV, GeoJSON  
        **Python Libraries**: pandas, numpy, folium, streamlit
        """)
    
    # User guide
    with st.expander("📖 User Guide", expanded=False):
        st.markdown("""
        1. **Site Evaluation**: Adjust MCDA weights in the "Site Evaluation" tab, generate and evaluate candidate sites
        2. **Decision Map**: View different types of analysis maps in the "Decision Map" tab
        3. **WMS Layers**: Select and overlay geographic background data in the "WMS Layers" tab
        4. **Data Management**: Generate, upload, and export data in the "Data Management" tab
        """)
    
    # Application statistics (if data exists)
    if hasattr(st.session_state, 'sites_data') and st.session_state.sites_data is not None:
        st.markdown("### 📊 Current Session Statistics")
        sites_count = len(st.session_state.sites_data)
        avg_score = st.session_state.sites_data['total_score'].mean() if 'total_score' in st.session_state.sites_data.columns else 0
        
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Evaluated Sites", sites_count)
        with metric_col2:
            st.metric("Average Score", f"{avg_score:.3f}" if avg_score > 0 else "Not Calculated")

def basic_map_view():
    """Basic Map View"""
    st.markdown("## Map Display")

    # Create a simple leaflet map
    try:
        m = folium.Map(
            location=[-36.8485, 174.7633],  # Auckland center
            zoom_start=10
        )
        
        # Add some sample markers
        folium.Marker(
            [-36.8485, 174.7633],
            popup="Auckland City Center",
            tooltip="Auckland City Center"
        ).add_to(m)
        
        st_folium(m, width=700, height=400)
        
    except Exception as e:
        st.error(f"Map loading failed: {e}")
        st.write("Please check if folium and streamlit-folium are installed correctly")

def wms_layers_view(geoserver_manager):
    """WMS Layer Display - Use Leaflet WMS component to avoid flicker"""
    st.markdown("## 🌐 GeoServer WMS Layers (Leaflet Version)")
    
    try:
        # Prefer Leaflet WMS viewer
        if LEAFLET_WMS_AVAILABLE:
            st.info("🍃 Using Leaflet.js to render WMS layers directly, avoiding map flicker")
            create_leaflet_wms_viewer_with_controls(geoserver_manager, container_key="main_leaflet_wms_viewer")
        else:
            st.error("❌ WMS component unavailable")
            st.write("Please check if Leaflet WMS component is imported correctly")
        
    except Exception as e:
        st.error(f"WMS layer view error: {e}")
        st.exception(e)

def data_overview():
    """Data Overview"""
    st.markdown("## Data Management")
    
    # Simple data display
    try:
        sample_data = pd.DataFrame({
            'Site Name': ['Candidate Site A', 'Candidate Site B', 'Candidate Site C'],
            'Score': [85, 78, 82],
            'Status': ['Recommended', 'Alternative', 'Alternative']
        })
        
        st.dataframe(sample_data, use_container_width=True)
        
    except Exception as e:
        st.error(f"Data loading failed: {e}")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        st.selectbox("Study Area", ["Auckland", "Wellington", "Christchurch"])
        
        st.slider("Population Weight", 0.0, 1.0, 0.3)
        st.slider("Risk Weight", 0.0, 1.0, 0.2)

def site_evaluation_view(geoserver_manager):
    """Site Evaluation View"""
    st.markdown("## 🎯 Site Evaluation and MCDA Analysis")
    
    try:
        # Initialize component
        site_evaluator = SiteEvaluator(geoserver_manager)
        # mcda_analyzer will be created and updated in the sidebar logic
        # and then assigned to site_evaluator.mcda_analyzer
        
        # Sidebar controls
        with st.sidebar:
            st.markdown("### 🎛️ MCDA Weight Settings")
            
            current_weights = {}
            current_weights['population_density'] = st.slider("Population Density Weight", 0.0, 1.0, st.session_state.get('mcda_weight_pop', 0.25), 0.05, key="mcda_pop_density_slider")
            current_weights['accessibility'] = st.slider("Accessibility Weight", 0.0, 1.0, st.session_state.get('mcda_weight_acc', 0.20), 0.05, key="mcda_accessibility_slider")
            current_weights['risk_level'] = st.slider("Risk Level Weight", 0.0, 1.0, st.session_state.get('mcda_weight_risk', 0.15), 0.05, key="mcda_risk_level_slider")
            current_weights['facility_capacity'] = st.slider("Facility Capacity Weight", 0.0, 1.0, st.session_state.get('mcda_weight_cap', 0.20), 0.05, key="mcda_facility_capacity_slider")
            current_weights['service_coverage'] = st.slider("Service Coverage Weight", 0.0, 1.0, st.session_state.get('mcda_weight_serv', 0.20), 0.05, key="mcda_service_coverage_slider")
            
            # Store weights in session state so they persist
            st.session_state.mcda_weight_pop = current_weights['population_density']
            st.session_state.mcda_weight_acc = current_weights['accessibility']
            st.session_state.mcda_weight_risk = current_weights['risk_level']
            st.session_state.mcda_weight_cap = current_weights['facility_capacity']
            st.session_state.mcda_weight_serv = current_weights['service_coverage']

            mcda_analyzer_sidebar = MCDAAnalyzer() # Create a new analyzer for sidebar configuration
            mcda_analyzer_sidebar.update_weights(current_weights) # Update it with current sidebar weights
            
            total_weight = sum(current_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                st.warning(f"⚠️ Total weight: {total_weight:.2f} (Recommended: 1.0)")
            else:
                st.success(f"✅ Total weight: {total_weight:.2f}")
            
            # Data source selection - only real data
            st.markdown("### 📊 Data Source Selection")
            
            # Dynamically get available facility files
            try:
                available_files = list_available_facility_files()
                if not available_files:
                    st.error("No facility data files found in data directory")
                    return
                
                # Friendly display names
                file_display_names = []
                for file in available_files:
                    if "real" in file:
                        file_display_names.append(f"{file} (Real Data)")
                    elif "prepared" in file:
                        file_display_names.append(f"{file} (Prepared Data)")
                    elif "qgis" in file:
                        file_display_names.append(f"{file} (QGIS Data)")
                    else:
                        file_display_names.append(f"{file}")
                
                selected_display = st.selectbox(
                    "Select Facility Data File",
                    file_display_names,
                    key="facility_data_source"
                )
                
                # Extract actual file name from display name
                selected_file = available_files[file_display_names.index(selected_display)]
                
            except Exception as e:
                st.error(f"Failed to get data file list: {e}")
                return
            
            st.info(f"📁 Currently Selected: {selected_file}")

            if st.button("🔄 Reload Data and Evaluate", key="site_eval_reload_and_eval"):
                # Clear cached data, force reload
                st.session_state.sites_data_for_evaluation = None 
                st.session_state.evaluated_sites_for_view = None
                st.session_state.selected_data_file = selected_file
        
        # Data loading logic - only use real CSV data
        if ('sites_data_for_evaluation' not in st.session_state or 
            st.session_state.sites_data_for_evaluation is None or
            'selected_data_file' not in st.session_state or
            st.session_state.get('selected_data_file') != selected_file):
            
            with st.spinner(f"Loading facility data from {selected_file}..."):
                try:
                    raw_sites_data = load_specific_facility_data(selected_file)
                    if raw_sites_data.empty:
                        st.error(f"Unable to load data from {selected_file}. Please check if the file exists.")
                        return
                    st.session_state.sites_data_for_evaluation = raw_sites_data
                    st.session_state.selected_data_file = selected_file
                    st.success(f"✅ Successfully loaded {len(raw_sites_data)} facilities")
                except Exception as e:
                    st.error(f"Error loading data: {e}")
                    return
        
        raw_sites_data_to_evaluate = st.session_state.sites_data_for_evaluation
        
        # Data preview
        with st.expander("📋 Raw Data Preview", expanded=False):
            if not raw_sites_data_to_evaluate.empty:
                st.markdown(f"**Data Source**: {st.session_state.get('selected_data_file', 'Unknown')}")
                st.markdown(f"**Data Volume**: {len(raw_sites_data_to_evaluate)} facilities")
                st.markdown(f"**Number of Columns**: {len(raw_sites_data_to_evaluate.columns)}")
                
                col_preview1, col_preview2 = st.columns(2)
                with col_preview1:
                    st.markdown("**Data Preview:**")
                    st.dataframe(raw_sites_data_to_evaluate.head(10), use_container_width=True)
                
                with col_preview2:
                    st.markdown("**Column Info:**")
                    for col in raw_sites_data_to_evaluate.columns:
                        col_type = str(raw_sites_data_to_evaluate[col].dtype)
                        non_null_count = raw_sites_data_to_evaluate[col].notna().sum()
                        st.write(f"• **{col}**: {col_type} ({non_null_count}/{len(raw_sites_data_to_evaluate)} non-null values)")
        
        # Check if reevaluation is needed
        weights_hash = hashlib.md5(str(sorted(current_weights.items())).encode()).hexdigest()
        need_reevaluation = (
            'evaluated_sites_for_view' not in st.session_state or 
            st.session_state.evaluated_sites_for_view is None or
            'last_weights_hash' not in st.session_state or
            st.session_state.last_weights_hash != weights_hash or
            'sites_data_for_evaluation' not in st.session_state or
            st.session_state.sites_data_for_evaluation is None
        )
        
        if need_reevaluation:
            with st.spinner("Performing site evaluation (MCDA)..."):
                # Assign the MCDA analyzer (configured from sidebar) to the site_evaluator instance
                site_evaluator.mcda_analyzer = mcda_analyzer_sidebar
                evaluated_sites = site_evaluator.evaluate_sites(raw_sites_data_to_evaluate.copy())
                st.session_state.evaluated_sites_for_view = evaluated_sites
                st.session_state.last_weights_hash = weights_hash  # Record weight hash
            
        if 'evaluated_sites_for_view' not in st.session_state or st.session_state.evaluated_sites_for_view is None:
            st.info("Please click 'Apply Settings and Re-evaluate' to see results.")
            return

        evaluated_sites_display = st.session_state.evaluated_sites_for_view
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📊 Evaluation Results")
            top_sites = evaluated_sites_display.nlargest(10, 'total_score')
            for idx, site_row in top_sites.iterrows(): # Renamed 'site' to 'site_row' to avoid conflict
                with st.expander(f"#{site_row['rank']} {site_row['name']} (Score: {site_row['total_score']:.3f})"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"📍 Coordinates: {site_row['latitude']:.4f}, {site_row['longitude']:.4f}")
                        st.write(f"👥 Population Density: {site_row.get('population_density', 'N/A'):.0f}")
                        st.write(f"🚗 Accessibility: {site_row.get('accessibility', 'N/A'):.2f}")
                    with col_b:
                        st.write(f"⚠️ Risk Level: {site_row.get('risk_level', 'N/A'):.2f}")
                        st.write(f"🏢 Facility Capacity: {site_row.get('facility_capacity', 'N/A'):.0f}")
                        st.write(f"🛍️ Service Coverage: {site_row.get('service_coverage', 'N/A'):.2f}")
        
        with col2:
            st.markdown("### 📈 Evaluation Statistics")
            st.metric("Total Candidate Sites", len(evaluated_sites_display))
            st.metric("Recommended Sites", len(evaluated_sites_display[evaluated_sites_display['total_score'] >= 0.6]))
            st.metric("Average Score", f"{evaluated_sites_display['total_score'].mean():.3f}")
            try:
                import plotly.express as px
                fig = px.histogram(evaluated_sites_display, x='total_score', nbins=20, title="Site Score Distribution")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.info("Install plotly to view charts: pip install plotly")
        
        with st.expander("📋 Detailed Evaluation Data", expanded=False):
            st.dataframe(evaluated_sites_display.sort_values('rank'), use_container_width=True)
        
        if st.button("💾 Export Evaluation Results", key="site_eval_export"):
            csv = evaluated_sites_display.to_csv(index=False)
            st.download_button(
                label="Download CSV File",
                data=csv,
                file_name=f"evacuation_sites_evaluation_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="site_eval_download"
            )
    
    except Exception as e:
        st.error(f"Error during site evaluation: {e}")
        st.exception(e) # Show full traceback for debugging
        st.write("Please check if components are installed correctly")

def decision_map_view(geoserver_manager):
    """Decision Support Map View"""
    st.markdown("## 🗺️ Decision Support Map")
    
    try:
        sites_data_for_map = None
        if 'evaluated_sites_for_view' in st.session_state and st.session_state.evaluated_sites_for_view is not None:
            sites_data_for_map = st.session_state.evaluated_sites_for_view
            st.info("Using evaluated data from the 'Site Evaluation' tab.")
        elif 'sites_data_for_evaluation' in st.session_state and st.session_state.sites_data_for_evaluation is not None:
            sites_data_for_map = st.session_state.sites_data_for_evaluation
            st.warning("Using raw site data. Please evaluate in 'Site Evaluation' for accurate map features.")
            if 'total_score' not in sites_data_for_map.columns:
                with st.spinner("Evaluating map data with default weights..."):
                    temp_site_evaluator = SiteEvaluator(geoserver_manager)
                    sites_data_for_map = temp_site_evaluator.evaluate_sites(sites_data_for_map.copy())
        else:
            st.sidebar.info("Map data not initialized, loading default facility data.")
            # Directly load real facility data
            try:
                available_files = list_available_facility_files()
                if available_files:
                    # Use the first available facility file
                    default_facility_file = available_files[0]
                    sites_data_for_map = load_specific_facility_data(default_facility_file)
                    if sites_data_for_map.empty:
                         st.error("Unable to load facility data for decision map. Please check CSV files in the data directory.")
                         return
                    with st.spinner("Evaluating facility data with default weights..."):
                        temp_site_evaluator = SiteEvaluator(geoserver_manager)
                        sites_data_for_map = temp_site_evaluator.evaluate_sites(sites_data_for_map.copy())
                    st.session_state.sites_data_for_evaluation = sites_data_for_map 
                    st.session_state.evaluated_sites_for_view = sites_data_for_map
                else:
                    st.error("No facility data files found in data directory")
                    return
            except Exception as e:
                st.error(f"Error loading facility data: {e}")
                return

        if sites_data_for_map is None or sites_data_for_map.empty:
            st.error("No site data available for map display. Please generate and evaluate data in the 'Site Evaluation' tab first.")
            return
            
        decision_map = DecisionSupportMap()
        map_type = st.selectbox(
            "Select Map Type",
            ["Site Evaluation Map", "Risk Assessment Map", "Scenario Comparison Map"],
            key="decision_map_type_selector"
        )
        
        selected_wms_layers_names = [] # Store names for DecisionSupportMap
        if geoserver_manager:
            with st.expander("🌐 Background Layer Selection (Leaflet)", expanded=False):
                try:
                    if LEAFLET_WMS_AVAILABLE:
                        st.info("🍃 Using Leaflet WMS layer selector")
                        selected_wms_layers_names = create_leaflet_background_layer_selector(
                            geoserver_manager, 
                            key_suffix="decision_map"
                        )
                    else:
                        st.warning("⚠️ Fallback to standard WMS layer selector")
                        selected_wms_layers_names = create_leaflet_background_layer_selector(
                            geoserver_manager, 
                            key_suffix="decision_map"
                        )
                except Exception as e_wms:
                    st.info(f"Unable to get WMS layers: {e_wms}")
        
        m = None 
        if map_type == "Site Evaluation Map":
            m = decision_map.create_site_evaluation_map(
                sites_data_for_map, geoserver_manager, selected_wms_layers_names 
            )
        elif map_type == "Risk Assessment Map":
            m = decision_map.create_risk_assessment_map(sites_data_for_map)
        else:  
            top_n_map = st.slider("Show Top N Scenarios", 3, 10, 5, key="decision_map_comparison_top_n_slider")
            m = decision_map.create_comparison_map(sites_data_for_map, top_n_map)
        
        if m:
            # Use fixed key to avoid refresh - key fix
            map_output_key = f"decision_map_display_{map_type}"
            map_data = st_folium(m, width=800, height=600, key=map_output_key)
            if map_data.get('last_object_clicked'):
                st.markdown("### 📍 Click Info")
                st.json(map_data['last_object_clicked'])
        else:
            st.info("Please select a map type to display the map.")
    
    except Exception as e:
        st.error(f"Error creating map: {e}")
        st.exception(e)
        # basic_map_view() # Consider if this fallback is always desired

# Coverage analysis feature completely removed to solve flicker issue

def data_management_view():
    """Data Management View"""
    st.markdown("## 📁 Data Management")
    
    # Data source selection
    data_source = st.selectbox(
        "Select Data Source",
        ["CSV File Upload", "GeoServer Data"]
    )
    
    if data_source == "CSV File Upload":
        st.markdown("### 📤 CSV File Upload")
        
        uploaded_file = st.file_uploader("Select CSV File", type=['csv'])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ File uploaded successfully! Contains {len(df)} rows")
                
                # Data preview
                st.markdown("#### Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Data info
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Field Info")
                    st.write(f"Number of Fields: {len(df.columns)}")
                    st.write("Field List:")
                    for col in df.columns:
                        st.write(f"- {col}: {df[col].dtype}")
                
                with col2:
                    st.markdown("#### Data Quality")
                    missing_data = df.isnull().sum()
                    if missing_data.sum() > 0:
                        st.warning("⚠️ Missing data found:")
                        for col, missing in missing_data[missing_data > 0].items():
                            st.write(f"- {col}: {missing} missing values")
                    else:
                        st.success("✅ Data complete, no missing values")
                
                # Save to session state
                st.session_state.uploaded_data = df
                
            except Exception as e:
                st.error(f"File read failed: {e}")
    
    else:  # GeoServer data
        st.markdown("### 🌐 GeoServer Data Management")
        
        if GEOSERVER_AVAILABLE:
            try:
                geoserver_manager = GeoServerManager("http://localhost:8080/geoserver", "admin", "admin")
                if geoserver_manager.test_connection():
                    st.success("✅ GeoServer connected successfully")
                    
                    # Show available layers
                    layers = geoserver_manager.get_all_layers_in_workspace("evacuation")
                    if layers:
                        st.markdown("#### Available Layers")
                        layer_df = pd.DataFrame(layers)
                        st.dataframe(layer_df, use_container_width=True)
                    else:
                        st.info("No layers in evacuation workspace")
                else:
                    st.warning("⚠️ Unable to connect to GeoServer")
            except Exception as e:
                st.error(f"GeoServer connection failed: {e}")
        else:
            st.error("GeoServer component unavailable")
    
    # Data export feature
    st.markdown("### 💾 Data Export")
    
    export_options = []
    if 'sites_data' in st.session_state:
        export_options.append("Evaluation Result Data")
    if 'evaluated_sites_for_view' in st.session_state:
        export_options.append("Site Evaluation Results")
    if 'uploaded_data' in st.session_state:
        export_options.append("Uploaded Data")
    
    if export_options:
        selected_export = st.selectbox("Select Data to Export", export_options)
        
        if st.button("📥 Export as CSV", key="data_mgmt_export"):
            if selected_export == "Evaluation Result Data":
                data_to_export = st.session_state.sites_data
            elif selected_export == "Site Evaluation Results":
                data_to_export = st.session_state.evaluated_sites_for_view
            else:  # Uploaded data
                data_to_export = st.session_state.uploaded_data
            
            csv = data_to_export.to_csv(index=False)
            st.download_button(
                label="Download CSV File",
                data=csv,
                file_name=f"{selected_export.replace(' ', '_')}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="data_mgmt_download"
            )
    else:
        st.info("No data available for export")

if __name__ == "__main__":
    main()
