#!/usr/bin/env python3
"""
PostGIS到GeoServer连接测试脚本
Test script for PostGIS to GeoServer connection

用于测试和演示PostGIS数据库到GeoServer的连接和数据发布功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.components.db_interface import PostGISGeoServerInterface
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主测试函数"""
    print("=== PostGIS到GeoServer连接测试 ===\n")
    
    # 数据库配置
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'postgres',
        'username': 'postgres',
        'password': 'postgres'
    }
    
    # GeoServer配置
    geoserver_config = {
        'base_url': 'http://localhost:8080/geoserver',
        'username': 'admin',
        'password': 'geoserver'
    }
    
    # 创建接口实例
    print("1. 创建PostGIS-GeoServer接口...")
    interface = PostGISGeoServerInterface(db_config, geoserver_config)
    
    # 测试连接
    print("\n2. 测试连接...")
    db_status, gs_status = interface.test_connections()
    
    print(f"   PostgreSQL/PostGIS连接: {'✅ 成功' if db_status else '❌ 失败'}")
    print(f"   GeoServer连接: {'✅ 成功' if gs_status else '❌ 失败'}")
    
    if not (db_status and gs_status):
        print("\n⚠️ 连接测试失败，请检查配置和服务状态")
        return
    
    # 获取PostGIS表
    print("\n3. 获取PostGIS空间表...")
    postgis_tables = interface.get_postgis_tables()
    
    if postgis_tables:
        print(f"   找到 {len(postgis_tables)} 个空间表:")
        for table in postgis_tables:
            print(f"   - {table['table_name']} ({table['geometry_type']}, SRID: {table['srid']})")
    else:
        print("   没有找到PostGIS空间表")
        print("   提示: 请确保数据库中存在包含几何字段的表")
        return
    
    # 创建工作空间和数据存储
    workspace = "auckland_emergency"
    store_name = "postgis_store"
    
    print(f"\n4. 创建PostGIS数据存储 '{store_name}' 在工作空间 '{workspace}'...")
    if interface.create_postgis_datastore(workspace, store_name):
        print("   ✅ PostGIS数据存储创建成功")
    else:
        print("   ❌ PostGIS数据存储创建失败")
        return
    
    # 发布第一个表作为图层
    if postgis_tables:
        first_table = postgis_tables[0]['table_name']
        layer_name = f"{first_table}_layer"
        
        print(f"\n5. 发布图层 '{layer_name}' (基于表 '{first_table}')...")
        if interface.publish_postgis_layer(workspace, store_name, first_table, layer_name):
            print("   ✅ 图层发布成功")
            
            # 显示服务URL
            wms_url = interface.get_layer_wms_url(workspace, layer_name)
            wfs_url = interface.get_layer_wfs_url(workspace, layer_name)
            
            print(f"\n6. 服务URL:")
            print(f"   WMS: {wms_url}")
            print(f"   WFS: {wfs_url}")
            
        else:
            print("   ❌ 图层发布失败")
    
    # 获取已发布的图层
    print(f"\n7. 获取数据存储 '{store_name}' 中的图层...")
    published_layers = interface.get_datastore_layers(workspace, store_name)
    
    if published_layers:
        print(f"   已发布的图层:")
        for layer in published_layers:
            print(f"   - {layer}")
    else:
        print("   没有已发布的图层")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()
