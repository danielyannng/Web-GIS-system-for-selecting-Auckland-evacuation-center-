#!/usr/bin/env python3
"""
Project Status Checker Script
"""

import subprocess
import requests
import psycopg2
import sys
from datetime import datetime

def check_docker():
    """Check Docker status"""
    print("🐳 Docker Status Check")
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        print(f"   ✅ Docker installed: {result.stdout.strip()}")
        return True
    except:
        print("   ❌ Docker not installed or unavailable")
        return False

def check_containers():
    """Check container status"""
    print("\n📦 Container Status Check")
    
    # Check PostgreSQL container
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=evacuation-postgres', '--format', '{{.Status}}'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   ✅ PostgreSQL container: {result.stdout.strip()}")
        else:
            print("   ❌ PostgreSQL container not running")
    except:
        print("   ❌ Unable to check PostgreSQL container")
    
    # Check GeoServer container
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=geoserver', '--format', '{{.Status}}'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   ✅ GeoServer container: {result.stdout.strip()}")
        else:
            print("   ❌ GeoServer container not running")
    except:
        print("   ❌ Unable to check GeoServer container")

def check_database():
    """Check database connection"""
    print("\n🗄️ Database Connection Check")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="postgres",
            dbname="evacuation"
        )
        cursor = conn.cursor()
        
        # Check table count
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            AND table_name != 'spatial_ref_sys'
        """)
        result = cursor.fetchone()
        table_count = result[0] if result else 0
        
        # Check spatial table count
        cursor.execute("SELECT COUNT(*) FROM geometry_columns")
        result = cursor.fetchone()
        spatial_count = result[0] if result else 0
        
        print(f"   ✅ Database connection successful")
        print(f"   📊 Tables: {table_count}")
        print(f"   🗺️ Spatial tables: {spatial_count}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

def check_geoserver():
    """Check GeoServer service"""
    print("\n🗺️ GeoServer Service Check")
    try:
        # Check basic connection
        response = requests.get("http://localhost:8080/geoserver/rest/about/version", 
                              auth=('admin', 'geoserver'), timeout=10)
        if response.status_code == 200:
            print("   ✅ GeoServer REST API available")
            
            # Check workspace
            response = requests.get("http://localhost:8080/geoserver/rest/workspaces/evacuation_workspace", 
                                  auth=('admin', 'geoserver'), timeout=10)
            if response.status_code == 200:
                print("   ✅ evacuation_workspace workspace exists")
                
                # Check layer count
                response = requests.get("http://localhost:8080/geoserver/rest/workspaces/evacuation_workspace/layers", 
                                      auth=('admin', 'geoserver'), timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    layers = data.get('layers', {}).get('layer', [])
                    layer_count = len(layers) if isinstance(layers, list) else 1 if layers else 0
                    print(f"   ✅ Published layers: {layer_count}")
                else:
                    print("   ⚠️ Unable to get layer information")
            else:
                print("   ❌ evacuation_workspace workspace does not exist")
        else:
            print(f"   ❌ GeoServer connection failed: HTTP {response.status_code}")
        return True
    except Exception as e:
        print(f"   ❌ GeoServer check failed: {e}")
        return False

def check_streamlit():
    """Check Streamlit app"""
    print("\n🖥️ Streamlit App Check")
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("   ✅ Streamlit app running (http://localhost:8501)")
        else:
            print(f"   ❌ Streamlit app abnormal response: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Streamlit app not running")
    except Exception as e:
        print(f"   ❌ Streamlit check failed: {e}")

def main():
    print("Evacuation Center Site Selection Decision Support System - Status Check")
    print("=" * 50)
    print(f"Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all checks
    docker_ok = check_docker()
    if docker_ok:
        check_containers()
    
    db_ok = check_database()
    geoserver_ok = check_geoserver()
    check_streamlit()
    
    print("\n" + "=" * 50)
    if docker_ok and db_ok and geoserver_ok:
        print("🎉 System status is good, ready to use!")
        print("\n📋 Access URLs:")
        print("   🖥️ Main app: http://localhost:8501")
        print("   ⚙️ GeoServer: http://localhost:8080/geoserver/web")
    else:
        print("⚠️ There are issues with the system, please check the above error messages")
        print("\n🔧 Suggested actions:")
        if not docker_ok:
            print("   - Install and start Docker")
        if not db_ok:
            print("   - Run: ./start.sh to start PostgreSQL")
        if not geoserver_ok:
            print("   - Run: cd scripts && docker-compose -f docker-compose-geoserver.yml up -d")

if __name__ == "__main__":
    main()
