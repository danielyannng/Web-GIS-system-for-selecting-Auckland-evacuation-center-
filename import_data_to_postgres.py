#!/usr/bin/env python3
"""
Data Import Tool - Import CSV files into PostgreSQL database
"""

import os
import pandas as pd
import glob
from sqlalchemy import create_engine, text
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection info - modify as needed
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "evacuation")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

# Print connection info
print(f"Database connection info:")
print(f"  Host: {DB_HOST}")
print(f"  Port: {DB_PORT}")
print(f"  Database: {DB_NAME}")
print(f"  User: {DB_USER}")
print(f"  Password: {'*' * len(DB_PASSWORD)}")

def create_database_if_not_exists():
    """Create database (if not exists) and enable PostGIS extension"""
    try:
        # Connect to the default 'postgres' database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        database_exists = cursor.fetchone() is not None
        
        if not database_exists:
            # Create database
            print(f"Creating database {DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created successfully!")
        else:
            print(f"Database {DB_NAME} already exists")
        
        cursor.close()
        conn.close()
        
        # Connect to the new database to enable PostGIS
        print("Enabling PostGIS extension...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            # Check if PostGIS is installed
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
            if cursor.fetchone() is None:
                # Create PostGIS extension
                print("Installing PostGIS extension...")
                cursor.execute("CREATE EXTENSION postgis")
                cursor.execute("CREATE EXTENSION postgis_topology")
                print("PostGIS extension installed successfully!")
            else:
                print("PostGIS extension already installed")
                
            # Check PostGIS version
            cursor.execute("SELECT PostGIS_Version()")
            version = cursor.fetchone()
            print(f"PostGIS version: {version[0] if version else 'Unknown'}")
            
        except Exception as e:
            print(f"Error enabling PostGIS extension: {e}")
            print("Warning: No PostGIS extension, geospatial features will not be available")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        raise

def get_connection_string():
    """Get database connection string"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def import_csv_to_postgres(csv_file):
    """Import CSV file into PostgreSQL database"""
    try:
        # Extract table name from file name
        table_name = os.path.basename(csv_file).split('.')[0].lower()
        
        print(f"Importing {csv_file} into table {table_name}...")
        
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Create database connection
        engine = create_engine(get_connection_string())
        
        # Import data
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        # If file contains geo data, try to add geo field
        has_geo_columns = False
        
        # Detect geo columns
        lat_col = next((col for col in df.columns if col.lower() in ['latitude', 'lat']), None)
        lon_col = next((col for col in df.columns if col.lower() in ['longitude', 'lon', 'lng']), None)
        wkt_col = next((col for col in df.columns if col.lower() in ['geom', 'geometry', 'wkt', 'shape']), None)
        
        if lat_col and lon_col:
            has_geo_columns = True
        elif wkt_col:
            has_geo_columns = True
            
        if has_geo_columns:
            try:
                with engine.connect() as connection:
                    # Ensure table has index and primary key
                    try:
                        connection.execute(text(f"""
                            DO $$
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_constraint WHERE conrelid = '{table_name}'::regclass AND contype = 'p'
                                ) THEN
                                    ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;
                                END IF;
                            END
                            $$;
                        """))
                    except Exception as e:
                        print(f"Error adding primary key: {e}")
                    
                    # Add geo field
                    if lat_col and lon_col:
                        print(f"Adding geospatial field using lat/lon columns {lat_col}/{lon_col}...")
                        connection.execute(text(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);
                            
                            UPDATE {table_name}
                            SET geom = ST_SetSRID(ST_MakePoint({lon_col}::float8, {lat_col}::float8), 4326)
                            WHERE {lon_col} IS NOT NULL AND {lat_col} IS NOT NULL;
                        """))
                    elif wkt_col:
                        print(f"Adding geospatial field using WKT column {wkt_col}...")
                        connection.execute(text(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326);
                            
                            UPDATE {table_name}
                            SET geom = ST_SetSRID(ST_GeomFromText({wkt_col}), 4326)
                            WHERE {wkt_col} IS NOT NULL;
                        """))
                    
                    # Create spatial index
                    try:
                        connection.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS {table_name}_geom_idx
                            ON {table_name} USING GIST (geom);
                        """))
                        print(f"Created spatial index for table {table_name}")
                    except Exception as e:
                        print(f"Error creating spatial index: {e}")
                        
                    print(f"Added geospatial field to table {table_name}")
            except Exception as e:
                print(f"Error adding geo field: {e}")
        
        print(f"Successfully imported {csv_file} into table {table_name}")
        
    except Exception as e:
        print(f"Error importing {csv_file}: {e}")

def verify_postgis():
    """Verify PostGIS installation and test functionality"""
    try:
        # Create database connection
        engine = create_engine(get_connection_string())
        with engine.connect() as connection:
            # Check if PostGIS is available
            postgis_version_result = connection.execute(text("SELECT PostGIS_Full_Version()")).fetchone()
            if postgis_version_result:
                print(f"\nPostGIS info:")
                print(f"  {postgis_version_result[0]}")
                
                # Show supported spatial reference systems
                print(f"\nSample supported spatial reference systems:")
                srid_result = connection.execute(text("""
                    SELECT srid, auth_name, auth_srid, proj4text 
                    FROM spatial_ref_sys 
                    WHERE srid IN (4326, 3857, 2193)
                """)).fetchall()
                
                for row in srid_result:
                    print(f"  SRID {row[0]} ({row[1]}:{row[2]})")
                
                # Test basic spatial functions
                print("\nVerifying spatial functions:")
                test_result = connection.execute(text("""
                    SELECT 
                        ST_AsText(ST_Buffer(ST_GeomFromText('POINT(174.7633 -36.8485)'), 0.1)) as buffer,
                        ST_Distance(
                            ST_GeomFromText('POINT(174.7633 -36.8485)'), 
                            ST_GeomFromText('POINT(174.8633 -36.7485)')
                        ) as distance
                """)).fetchone()
                
                if test_result:
                    print(f"  Spatial buffer and distance calculation - Success!")
                    return True
            
            print("Warning: Unable to verify PostGIS functionality")
            return False
    except Exception as e:
        print(f"Error verifying PostGIS: {e}")
        return False

def main():
    """Main function"""
    print("PostgreSQL Data Import Tool")
    print("=" * 50)
    
    # Create database (if not exists) and enable PostGIS extension
    create_database_if_not_exists()
    
    # Verify PostGIS functionality
    verify_postgis()
    
    # Import all CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    print(f"Looking for CSV files in: {data_dir}")
    
    # Check if path exists
    if not os.path.exists(data_dir):
        print(f"Warning: Data directory {data_dir} does not exist, trying another location...")
        # Try parent directory
        parent_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(parent_dir, 'data')
        print(f"Trying alternative path: {data_dir}")
    
    # Ensure directory is found
    if not os.path.exists(data_dir):
        print(f"Error: Unable to find data directory")
        return
        
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {data_dir}")
        return
    
    print(f"Found {len(csv_files)} CSV files")
    
    # Import each CSV file
    for csv_file in csv_files:
        import_csv_to_postgres(csv_file)
    
    print("Import complete!")

if __name__ == "__main__":
    main()
