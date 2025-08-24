#!/usr/bin/env python3
"""
GIS数据导入工具 - 将Shapefile和其他GIS数据导入PostgreSQL/PostGIS
GIS Data Import Tool - Import Shapefiles and other GIS data into PostgreSQL/PostGIS
"""

import os
import sys
import glob
import subprocess
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 数据库连接信息 - 根据实际情况修改
DB_HOST = os.environ.get("DB_HOST", "localhost")  # 可通过环境变量设置或使用默认值
DB_PORT = os.environ.get("DB_PORT", "5432")       # PostgreSQL默认端口
DB_NAME = os.environ.get("DB_NAME", "evacuation") # 数据库名称
DB_USER = os.environ.get("DB_USER", "postgres")   # 数据库用户名
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres") # 数据库密码

# 打印连接信息
print(f"数据库连接信息:")
print(f"  主机: {DB_HOST}")
print(f"  端口: {DB_PORT}")
print(f"  数据库: {DB_NAME}")
print(f"  用户: {DB_USER}")
print(f"  密码: {'*' * len(DB_PASSWORD)}")

def create_database_if_not_exists():
    """创建数据库（如果不存在）并启用PostGIS扩展"""
    try:
        # 连接到默认的postgres数据库
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        database_exists = cursor.fetchone() is not None
        
        if not database_exists:
            # 创建数据库
            print(f"创建数据库 {DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"数据库 {DB_NAME} 创建成功！")
        else:
            print(f"数据库 {DB_NAME} 已存在")
        
        cursor.close()
        conn.close()
        
        # 连接到新创建的数据库以启用PostGIS
        print("正在启用PostGIS扩展...")
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
            # 检查PostGIS是否已安装
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
            if cursor.fetchone() is None:
                # 创建PostGIS扩展
                print("安装PostGIS扩展...")
                cursor.execute("CREATE EXTENSION postgis")
                cursor.execute("CREATE EXTENSION postgis_topology")
                print("PostGIS扩展安装成功！")
            else:
                print("PostGIS扩展已安装")
                
            # 验证PostGIS版本
            cursor.execute("SELECT PostGIS_Version()")
            version = cursor.fetchone()
            print(f"PostGIS版本: {version[0] if version else '未知'}")
            
        except Exception as e:
            print(f"启用PostGIS扩展时出错: {e}")
            print("警告: 没有PostGIS扩展，地理空间功能将不可用")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"创建数据库时出错: {e}")
        raise

def get_connection_string():
    """获取数据库连接字符串"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_ogr2ogr_connection_string():
    """获取用于ogr2ogr的数据库连接字符串"""
    return f"PG:host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

def check_ogr2ogr():
    """检查ogr2ogr是否已安装"""
    try:
        result = subprocess.run(["ogr2ogr", "--version"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        if result.returncode == 0:
            print(f"检测到ogr2ogr: {result.stdout.strip()}")
            return True
        else:
            print("警告: 未检测到ogr2ogr。请安装GDAL/OGR工具包。")
            print("可以通过以下命令安装:")
            print("  - macOS: brew install gdal")
            print("  - Ubuntu: sudo apt-get install gdal-bin")
            print("  - Windows: 使用OSGeo4W安装包")
            return False
    except FileNotFoundError:
        print("警告: 未检测到ogr2ogr。请安装GDAL/OGR工具包。")
        return False

def get_shapefile_layers():
    """查找数据目录中的Shapefile图层"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 查找数据目录
    data_dir = os.path.join(script_dir, 'data')
    if not os.path.exists(data_dir):
        parent_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(parent_dir, 'data')
    
    if not os.path.exists(data_dir):
        print(f"错误: 无法找到数据目录")
        return []
        
    qgis_data_dir = os.path.join(data_dir, 'QGIS Data')
    if not os.path.exists(qgis_data_dir):
        print(f"错误: 无法找到QGIS数据目录: {qgis_data_dir}")
        return []
    
    print(f"在 {qgis_data_dir} 中查找Shapefile...")
    
    # 查找所有.shp文件
    shapefile_paths = []
    for root, _, files in os.walk(qgis_data_dir):
        for file in files:
            if file.endswith('.shp'):
                shapefile_paths.append(os.path.join(root, file))
    
    print(f"找到 {len(shapefile_paths)} 个Shapefile文件")
    return shapefile_paths

def import_shapefile(shapefile_path):
    """使用ogr2ogr将Shapefile导入PostgreSQL"""
    try:
        # 从路径中提取图层名
        base_name = os.path.basename(shapefile_path)
        layer_name = os.path.splitext(base_name)[0].lower().replace('.', '_')
        layer_name = layer_name.replace('-', '_')  # 替换不支持的字符
        
        # 构建ogr2ogr命令
        pg_conn_string = get_ogr2ogr_connection_string()
        
        print(f"\n导入 {os.path.basename(shapefile_path)} 到表 {layer_name}...")
        
        # 使用ogr2ogr导入shapefile
        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL", 
            pg_conn_string,
            shapefile_path,
            "-nln", layer_name,  # 设置图层名
            "-lco", "GEOMETRY_NAME=geom",  # 指定几何字段名
            "-lco", "FID=id",  # 指定主键字段名
            "-lco", "PRECISION=NO",  # 保持精度
            "-nlt", "PROMOTE_TO_MULTI",  # 将单一几何图形提升为多几何图形
            "-a_srs", "EPSG:4326",  # 设定坐标系统
            "--config", "PG_USE_COPY", "YES",  # 使用COPY提高性能
            "-overwrite"  # 如果存在则覆盖
        ]
        
        # 执行命令
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            print(f"成功导入 {layer_name}")
            return True
        else:
            print(f"导入 {layer_name} 时出错:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"导入Shapefile时出错: {e}")
        return False

def create_spatial_indexes(shapefile_paths):
    """为导入的图层创建空间索引"""
    try:
        # 连接到数据库
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("\n为导入的图层创建空间索引...")
        
        # 为每个导入的图层创建索引
        for shapefile_path in shapefile_paths:
            base_name = os.path.basename(shapefile_path)
            layer_name = os.path.splitext(base_name)[0].lower().replace('.', '_')
            layer_name = layer_name.replace('-', '_')  # 替换不支持的字符
            
            try:
                # 检查表是否存在
                cursor.execute(f"SELECT to_regclass('{layer_name}')")
                result = cursor.fetchone()
                if result and result[0] is not None:
                    # 创建空间索引
                    index_name = f"{layer_name}_geom_idx"
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {layer_name} USING GIST (geom)")
                    print(f"  为表 {layer_name} 创建空间索引")
            except Exception as e:
                print(f"  为表 {layer_name} 创建索引时出错: {e}")
        
        cursor.close()
        conn.close()
        print("空间索引创建完成")
        
    except Exception as e:
        print(f"创建空间索引时出错: {e}")

def analyze_imported_layers(shapefile_paths):
    """分析导入的图层，显示统计信息"""
    try:
        # 连接到数据库
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        cursor = conn.cursor()
        
        print("\n导入的图层统计信息:")
        
        # 为每个导入的图层显示统计信息
        for shapefile_path in shapefile_paths:
            base_name = os.path.basename(shapefile_path)
            layer_name = os.path.splitext(base_name)[0].lower().replace('.', '_')
            layer_name = layer_name.replace('-', '_')  # 替换不支持的字符
            
            try:
                # 检查表是否存在
                cursor.execute(f"SELECT to_regclass('{layer_name}')")
                result = cursor.fetchone()
                if not result or result[0] is None:
                    print(f"  表 {layer_name} 不存在")
                    continue
                
                # 获取记录数
                cursor.execute(f"SELECT COUNT(*) FROM {layer_name}")
                result = cursor.fetchone()
                count = result[0] if result else 0
                
                # 获取几何类型
                cursor.execute(f"""
                    SELECT 
                        DISTINCT GeometryType(geom) as geometry_type,
                        COUNT(*) as count
                    FROM 
                        {layer_name}
                    GROUP BY 
                        geometry_type
                """)
                geom_types = cursor.fetchall() or []
                
                # 获取边界框
                cursor.execute(f"""
                    SELECT 
                        ST_AsText(ST_Envelope(ST_Extent(geom))) as bbox
                    FROM 
                        {layer_name}
                """)
                result = cursor.fetchone()
                bbox = result[0] if result else "未知"
                
                # 打印统计信息
                print(f"\n  表 {layer_name}:")
                print(f"    记录数: {count}")
                print(f"    几何类型: {', '.join([f'{t[0]} ({t[1]})' for t in geom_types])}")
                print(f"    边界框: {bbox}")
            except Exception as e:
                print(f"  为表 {layer_name} 获取统计信息时出错: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"分析导入的图层时出错: {e}")

def main():
    """主函数"""
    print("GIS数据导入工具")
    print("=" * 50)
    
    # 检查ogr2ogr是否已安装
    if not check_ogr2ogr():
        print("请安装ogr2ogr后再运行此脚本")
        sys.exit(1)
    
    # 创建数据库和PostGIS扩展
    create_database_if_not_exists()
    
    # 获取shapefile文件路径
    shapefile_paths = get_shapefile_layers()
    
    if not shapefile_paths:
        print("没有找到Shapefile文件")
        sys.exit(1)
    
    # 导入每个shapefile
    imported_files = []
    for shapefile_path in shapefile_paths:
        if import_shapefile(shapefile_path):
            imported_files.append(shapefile_path)
    
    # 为导入的图层创建空间索引
    if imported_files:
        create_spatial_indexes(imported_files)
        analyze_imported_layers(imported_files)
    
    print("\nGIS数据导入完成！")

if __name__ == "__main__":
    main()
