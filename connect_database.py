#!/usr/bin/env python3
"""
数据库连接测试脚本
Database Connection Test Script

测试PostgreSQL数据库连接并创建基础结构
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from utils.db_connector import PostgreSQLConnector, DEFAULT_DB_CONFIG
import pandas as pd
import geopandas as gpd
from sqlalchemy import text
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    
    # 显示连接配置
    print(f"连接配置:")
    print(f"  主机: {DEFAULT_DB_CONFIG['host']}")
    print(f"  端口: {DEFAULT_DB_CONFIG['port']}")
    print(f"  数据库: {DEFAULT_DB_CONFIG['database']}")
    print(f"  用户: {DEFAULT_DB_CONFIG['username']}")
    print()
    
    # 创建连接器
    db = PostgreSQLConnector(**DEFAULT_DB_CONFIG)
    
    # 测试连接
    print("测试数据库连接...")
    if db.test_connection():
        print("✅ 数据库连接成功!")
    else:
        print("❌ 数据库连接失败!")
        return False
    
    # 启用PostGIS
    print("\n启用PostGIS扩展...")
    if db.enable_postgis():
        print("✅ PostGIS扩展已启用!")
    else:
        print("❌ PostGIS扩展启用失败!")
    
    # 获取现有表
    print("\n获取数据库表列表...")
    tables = db.get_tables()
    if tables:
        print(f"找到 {len(tables)} 个表:")
        for table in tables[:10]:  # 只显示前10个
            print(f"  - {table}")
        if len(tables) > 10:
            print(f"  ... 和其他 {len(tables) - 10} 个表")
    else:
        print("数据库中没有找到表")
    
    # 获取几何表
    print("\n获取空间表列表...")
    geo_tables = db.get_geometry_tables()
    if geo_tables:
        print(f"找到 {len(geo_tables)} 个空间表:")
        for table in geo_tables:
            print(f"  - {table['table_name']} ({table['geometry_type']}, SRID: {table['srid']})")
    else:
        print("数据库中没有找到空间表")
    
    return True

def create_sample_data():
    """创建示例数据"""
    print("\n" + "=" * 60)
    print("创建示例数据")
    print("=" * 60)
    
    db = PostgreSQLConnector(**DEFAULT_DB_CONFIG)
    
    # 创建简单的数据表
    print("创建示例人口数据表...")
    sample_data = pd.DataFrame({
        'region_id': [1, 2, 3, 4, 5],
        'region_name': ['Central Auckland', 'North Shore', 'West Auckland', 'South Auckland', 'East Auckland'],
        'population': [120000, 95000, 85000, 110000, 75000],
        'area_km2': [45.2, 38.7, 62.3, 55.1, 42.8],
        'density': [2654.9, 2454.0, 1364.5, 1996.4, 1752.3]
    })
    
    if db.create_table_from_dataframe(sample_data, 'sample_population'):
        print("✅ 示例人口数据表创建成功!")
    else:
        print("❌ 示例人口数据表创建失败!")
    
    # 创建简单的空间数据表
    print("\n创建示例空间数据表...")
    # 创建简单的点数据
    from shapely.geometry import Point
    
    sample_points = gpd.GeoDataFrame({
        'facility_id': [1, 2, 3, 4, 5],
        'facility_name': ['Hospital A', 'Fire Station B', 'Police C', 'School D', 'Community Center E'],
        'facility_type': ['hospital', 'fire_station', 'police', 'school', 'community'],
        'capacity': [500, 50, 30, 800, 200],
        'geometry': [
            Point(174.7633, -36.8485),  # Auckland CBD
            Point(174.7433, -36.8585),
            Point(174.7833, -36.8385),
            Point(174.7533, -36.8685),
            Point(174.7733, -36.8285)
        ]
    }, crs='EPSG:4326')
    
    if db.create_spatial_table_from_geodataframe(sample_points, 'sample_facilities'):
        print("✅ 示例空间数据表创建成功!")
    else:
        print("❌ 示例空间数据表创建失败!")

def verify_data():
    """验证数据"""
    print("\n" + "=" * 60)
    print("验证数据")
    print("=" * 60)
    
    db = PostgreSQLConnector(**DEFAULT_DB_CONFIG)
    
    # 查看人口数据
    print("查看示例人口数据:")
    pop_data = db.read_table('sample_population', limit=5)
    if pop_data is not None:
        print(pop_data.to_string(index=False))
    else:
        print("无法读取人口数据")
    
    # 查看空间数据
    print("\n查看示例设施数据:")
    facility_data = db.read_spatial_table('sample_facilities', limit=5)
    if facility_data is not None:
        # 不显示几何列的详细信息
        display_data = facility_data.drop('geometry', axis=1)
        print(display_data.to_string(index=False))
        print(f"几何类型: {facility_data.geometry.geom_type.iloc[0]}")
        print(f"坐标系: {facility_data.crs}")
    else:
        print("无法读取设施数据")

def main():
    """主函数"""
    try:
        # 测试连接
        if not test_database_connection():
            print("\n❌ 数据库连接测试失败，请检查配置!")
            return
        
        # 创建示例数据
        create_sample_data()
        
        # 验证数据
        verify_data()
        
        print("\n" + "=" * 60)
        print("✅ 数据库连接和设置完成!")
        print("=" * 60)
        print("\n现在可以:")
        print("1. 运行 Streamlit 应用: python run_app.py")
        print("2. 导入更多数据: python import_data_simple.py")
        print("3. 设置 GeoServer 连接")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        logger.exception("数据库连接过程中发生错误")

if __name__ == "__main__":
    main()
