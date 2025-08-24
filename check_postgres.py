#!/usr/bin/env python3
"""
PostgreSQL Connection Test Tool
"""

import psycopg2
import os
import sys
import subprocess

def test_postgres_connection():
    """Test PostgreSQL connection"""
    # Database connection info
    db_host = os.environ.get("DB_HOST", "localhost") 
    db_port = os.environ.get("DB_PORT", "5432")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    
    print(f"Attempting to connect to PostgreSQL...")
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"User: {db_user}")
    
    try:
        # Try connecting to the default 'postgres' database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname="postgres"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        if version:
            print(f"Connection successful! PostgreSQL version: {version[0]}")
        else:
            print("Connection successful! But could not retrieve PostgreSQL version info")
        
        # Check PostGIS extension
        try:
            cursor.execute("SELECT PostGIS_version();")
            postgis_version = cursor.fetchone()
            if postgis_version:
                print(f"PostGIS enabled, version: {postgis_version[0]}")
            else:
                print("PostGIS may be enabled, but could not retrieve version info")
        except:
            print("Warning: PostGIS extension not enabled. Importing geospatial data may fail.")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

def check_docker_postgres():
    """Check for PostgreSQL container in Docker"""
    try:
        # Check Docker containers
        print("Searching for PostgreSQL container in Docker...")
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres", "--format", "{{.ID}}  {{.Names}}  {{.Ports}}"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("Found PostgreSQL container:")
            print(result.stdout.strip())
            
            # Get container ID
            container_id = result.stdout.split()[0]
            
            # Get container IP
            ip_result = subprocess.run(
                ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_id],
                capture_output=True,
                text=True
            )
            
            container_ip = ip_result.stdout.strip()
            if container_ip:
                print(f"Container IP: {container_ip}")
                print("Tip: Try using this IP as the database host address")
        else:
            print("No running PostgreSQL container found")
    except Exception as e:
        print(f"Error checking Docker containers: {e}")

if __name__ == "__main__":
    print("PostgreSQL Connection Test Tool")
    print("=" * 50)
    
    connection_ok = test_postgres_connection()
    
    if not connection_ok:
        print("\nTrying to check for PostgreSQL container in Docker...")
        check_docker_postgres()
        
        print("\nTips:")
        print("1. Make sure the PostgreSQL container is running")
        print("2. Check if the container port is mapped correctly")
        print("3. Use the correct host address (container IP or mapped hostname)")
        print("4. Verify the username and password are correct")
