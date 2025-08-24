# Project Configuration File

# Application Information
APP_NAME = "Evacuation Center Site Selection Decision Support System"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Web GIS-based Evacuation Center Site Selection Decision Support System"

# Server Port Configuration
STREAMLIT_PORT = 8501
GEOSERVER_PORT = 8080
POSTGRES_PORT = 5432

# Database Configuration
POSTGRES_HOST = "localhost"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_DB = "evacuation"

# GeoServer Configuration
GEOSERVER_URL = "http://localhost:8080/geoserver"
GEOSERVER_USER = "admin"
GEOSERVER_PASSWORD = "geoserver"
GEOSERVER_WORKSPACE = "evacuation_workspace"
GEOSERVER_DATASTORE = "evacuation_postgis"

# Data Paths
DATA_DIR = "./data"
QGIS_DATA_DIR = "./data/QGIS Data"

# Application Settings
ENABLE_CACHING = True
CACHE_TTL = 3600  # 1 hour
DEBUG_MODE = False
