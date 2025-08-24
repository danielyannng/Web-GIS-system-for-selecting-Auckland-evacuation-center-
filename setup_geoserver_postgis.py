#!/usr/bin/env python3
"""
GeoServer PostGIS连接设置脚本
GeoServer PostGIS Connection Setup Script

在GeoServer中创建PostGIS数据源并发布图层
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

# GeoServer配置
GEOSERVER_CONFIG = {
    'base_url': 'http://localhost:8080/geoserver',
    'username': 'admin',
    'password': 'geoserver'
}

def test_geoserver_connection():
    """测试GeoServer连接"""
    print("=" * 60)
    print("GeoServer连接测试")
    print("=" * 60)
    
    geoserver = GeoServerManager(**GEOSERVER_CONFIG)
    
    print(f"连接配置:")
    print(f"  URL: {GEOSERVER_CONFIG['base_url']}")
    print(f"  用户: {GEOSERVER_CONFIG['username']}")
    print()
    
    print("测试GeoServer连接...")
    if geoserver.test_connection():
        print("✅ GeoServer连接成功!")
        return geoserver
    else:
        print("❌ GeoServer连接失败!")
        print("请确保:")
        print("1. GeoServer已启动并运行在 http://localhost:8080/geoserver")
        print("2. 用户名和密码正确 (默认: admin/geoserver)")
        return None

def create_postgis_datastore(geoserver, workspace_name='evacuation'):
    """创建PostGIS数据存储"""
    print("\n" + "=" * 60)
    print("创建PostGIS数据存储")
    print("=" * 60)
    
    # 创建工作空间
    print(f"创建工作空间: {workspace_name}")
    if geoserver.create_workspace(workspace_name):
        print(f"✅ 工作空间 '{workspace_name}' 创建成功!")
    else:
        print(f"⚠️  工作空间 '{workspace_name}' 可能已存在")
    
    datastore_name = 'postgis_evacuation'
    print(f"\n创建PostGIS数据存储: {datastore_name}")
    
    if geoserver.create_postgis_datastore(
        workspace_name, 
        datastore_name, 
        DEFAULT_DB_CONFIG['host'],
        DEFAULT_DB_CONFIG['port'],
        DEFAULT_DB_CONFIG['database'],
        DEFAULT_DB_CONFIG['username'],
        DEFAULT_DB_CONFIG['password']
    ):
        print(f"✅ PostGIS数据存储 '{datastore_name}' 创建成功!")
        return datastore_name
    else:
        print(f"❌ PostGIS数据存储 '{datastore_name}' 创建失败!")
        return None

def publish_spatial_layers(geoserver, workspace_name, datastore_name):
    """发布空间图层"""
    print("\n" + "=" * 60)
    print("发布空间图层")
    print("=" * 60)
    
    # 获取数据库中的空间表
    db = PostgreSQLConnector(**DEFAULT_DB_CONFIG)
    geo_tables = db.get_geometry_tables()
    
    if not geo_tables:
        print("没有找到空间表")
        return
    
    print(f"找到 {len(geo_tables)} 个空间表")
    
    # 发布主要的几个表
    priority_tables = [
        'auckland_facilities_data_real',
        'auckland_population_data_real', 
        'auckland_roads_data_real',
        'emergency_services_data_real',
        'sample_facilities',
        'facilities_prepared',
        'population_prepared'
    ]
    
    published_count = 0
    
    for table_info in geo_tables:
        table_name = table_info['table_name']
        
        # 优先发布重要表
        if table_name in priority_tables or published_count < 5:
            print(f"\n发布图层: {table_name}")
            
            if geoserver.publish_postgis_layer(workspace_name, datastore_name, table_name):
                print(f"✅ 图层 '{table_name}' 发布成功!")
                published_count += 1
            else:
                print(f"❌ 图层 '{table_name}' 发布失败!")
            
            # 限制发布数量以避免过多请求
            if published_count >= 10:
                print(f"\n已发布 {published_count} 个图层，停止发布更多图层")
                break
    
    print(f"\n总计发布了 {published_count} 个图层")

def create_layer_groups(geoserver, workspace_name):
    """创建图层组"""
    print("\n" + "=" * 60)
    print("创建图层组")
    print("=" * 60)
    
    # 获取已发布的图层
    layers = geoserver.get_layers(workspace_name)
    
    if not layers:
        print("没有找到已发布的图层")
        return
    
    # 创建疏散相关图层组
    evacuation_layers = [layer for layer in layers if any(keyword in layer.lower() 
                        for keyword in ['facilities', 'emergency', 'population'])]
    
    if evacuation_layers:
        group_name = 'evacuation_layers'
        print(f"创建图层组: {group_name}")
        print(f"包含图层: {', '.join(evacuation_layers)}")
        
        if geoserver.create_layer_group(workspace_name, group_name, evacuation_layers):
            print(f"✅ 图层组 '{group_name}' 创建成功!")
        else:
            print(f"❌ 图层组 '{group_name}' 创建失败!")

def verify_setup(geoserver, workspace_name):
    """验证设置"""
    print("\n" + "=" * 60)
    print("验证GeoServer设置")
    print("=" * 60)
    
    # 列出工作空间
    workspaces = geoserver.get_workspaces()
    print(f"工作空间列表: {', '.join(workspaces)}")
    
    # 列出数据存储
    # datastores = geoserver.get_datastores(workspace_name)
    # print(f"数据存储列表: {', '.join(datastores)}")
    
    # 列出图层
    layers = geoserver.get_layers(workspace_name)
    print(f"图层列表 ({len(layers)} 个):")
    for layer in layers:
        print(f"  - {layer}")
    
    # 提供访问URL
    if layers:
        print(f"\n图层访问示例:")
        sample_layer = layers[0]
        wms_url = f"{GEOSERVER_CONFIG['base_url']}/{workspace_name}/wms"
        print(f"WMS服务: {wms_url}")
        print(f"图层预览: {GEOSERVER_CONFIG['base_url']}/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage")

def main():
    """主函数"""
    try:
        # 测试GeoServer连接
        geoserver = test_geoserver_connection()
        if not geoserver:
            return
        
        workspace_name = 'evacuation'
        
        # 创建PostGIS数据存储
        datastore_name = create_postgis_datastore(geoserver, workspace_name)
        if not datastore_name:
            return
        
        # 发布空间图层
        publish_spatial_layers(geoserver, workspace_name, datastore_name)
        
        # 创建图层组
        # create_layer_groups(geoserver, workspace_name)
        
        # 验证设置
        verify_setup(geoserver, workspace_name)
        
        print("\n" + "=" * 60)
        print("✅ GeoServer PostGIS连接设置完成!")
        print("=" * 60)
        print("\n现在可以:")
        print(f"1. 访问GeoServer管理界面: {GEOSERVER_CONFIG['base_url']}/web")
        print("2. 查看图层预览")
        print("3. 在Streamlit应用中使用WMS服务")
        print("4. 运行应用: python run_app.py")
        
    except Exception as e:
        print(f"\n❌ 设置过程中发生错误: {e}")
        logger.exception("GeoServer设置过程中发生错误")

if __name__ == "__main__":
    main()
