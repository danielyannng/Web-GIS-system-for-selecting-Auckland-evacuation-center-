#!/usr/bin/env python3
"""
简化的PostGIS图层发布脚本
Simplified PostGIS Layer Publishing Script
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from utils.geoserver_manager import GeoServerManager
from utils.db_connector import PostgreSQLConnector, DEFAULT_DB_CONFIG
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def publish_layers():
    """发布PostGIS图层到GeoServer"""
    
    # 连接GeoServer
    geoserver = GeoServerManager('http://localhost:8080/geoserver', 'admin', 'geoserver')
    
    if not geoserver.test_connection():
        print("❌ 无法连接到GeoServer")
        return
    
    print("✅ GeoServer连接成功")
    
    # 连接数据库
    db = PostgreSQLConnector(**DEFAULT_DB_CONFIG)
    if not db.test_connection():
        print("❌ 无法连接到数据库")
        return
    
    print("✅ 数据库连接成功")
    
    # 获取空间表
    geo_tables = db.get_geometry_tables()
    print(f"找到 {len(geo_tables)} 个空间表")
    
    workspace = 'evacuation'
    datastore = 'postgis_evacuation'
    
    # 发布几个重要的表
    tables_to_publish = [
        'sample_facilities',
        'auckland_facilities_data_real',
        'emergency_services_data_real',
        'population_prepared',
        'facilities_prepared'
    ]
    
    published = 0
    for table_name in tables_to_publish:
        print(f"\n尝试发布图层: {table_name}")
        
        # 检查表是否存在
        table_exists = any(t['table_name'] == table_name for t in geo_tables)
        if not table_exists:
            print(f"⚠️  表 {table_name} 不存在，跳过")
            continue
        
        # 发布图层
        try:
            if geoserver.publish_postgis_layer(workspace, datastore, table_name):
                print(f"✅ 图层 {table_name} 发布成功")
                published += 1
            else:
                print(f"❌ 图层 {table_name} 发布失败")
        except Exception as e:
            print(f"❌ 发布图层 {table_name} 时出错: {e}")
    
    print(f"\n总计发布了 {published} 个图层")
    
    if published > 0:
        print("\n可以在以下URL查看图层:")
        print("- GeoServer管理界面: http://localhost:8080/geoserver/web")
        print("- 图层预览: http://localhost:8080/geoserver/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage")
        print(f"- WMS服务: http://localhost:8080/geoserver/{workspace}/wms")

if __name__ == "__main__":
    publish_layers()
