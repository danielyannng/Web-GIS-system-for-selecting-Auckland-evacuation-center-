"""
GeoServer Configuration File

Set GeoServer connection parameters and offline mode configuration
"""

# GeoServer configuration
GEOSERVER_CONFIG = {
    "base_url": "http://localhost:8080/geoserver",
    "username": "admin",
    "password": "geoserver",
    "offline_mode": True  # Enable offline mode
}

def get_geoserver_config():
    """Get GeoServer configuration parameters"""
    return GEOSERVER_CONFIG
