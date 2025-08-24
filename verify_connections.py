#!/usr/bin/env python3
"""
系统连接验证脚本
System Connection Verification Script

验证整个疏散系统的所有连接
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from utils.geoserver_manager import GeoServerManager
from utils.db_connector import PostgreSQLConnector, DEFAULT_DB_CONFIG
import requests
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database():
    """检查数据库连接"""
    print("1️⃣ 检查PostgreSQL/PostGIS数据库连接...")
    
    try:
        db = PostgreSQLConnector(**DEFAULT_DB_CONFIG)
        if db.test_connection():
            print("✅ 数据库连接成功")
            
            # 检查PostGIS
            if db.enable_postgis():
                print("✅ PostGIS扩展已启用")
            
            # 获取表统计
            tables = db.get_tables()
            geo_tables = db.get_geometry_tables()
            print(f"📊 数据库统计: {len(tables)} 个表, {len(geo_tables)} 个空间表")
            
            return True
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 数据库检查出错: {e}")
        return False

def check_geoserver():
    """检查GeoServer连接"""
    print("\n2️⃣ 检查GeoServer连接...")
    
    try:
        geoserver = GeoServerManager('http://localhost:8080/geoserver', 'admin', 'geoserver')
        if geoserver.test_connection():
            print("✅ GeoServer连接成功")
            
            # 检查工作空间
            workspaces = geoserver.get_workspaces()
            print(f"📁 工作空间: {', '.join(workspaces)}")
            
            # 检查evacuation工作空间的图层
            if 'evacuation' in workspaces:
                layers = geoserver.get_layers('evacuation')
                print(f"🗺️  evacuation工作空间图层: {len(layers)} 个")
                if layers:
                    print(f"   图层列表: {', '.join([layer.get('name', 'unknown') for layer in layers[:5]])}")
            
            return True
        else:
            print("❌ GeoServer连接失败")
            return False
    except Exception as e:
        print(f"❌ GeoServer检查出错: {e}")
        return False

def check_streamlit():
    """检查Streamlit应用"""
    print("\n3️⃣ 检查Streamlit应用...")
    
    try:
        response = requests.get('http://localhost:8501', timeout=10)
        if response.status_code == 200:
            print("✅ Streamlit应用运行正常")
            print("🌐 应用地址: http://localhost:8501")
            return True
        else:
            print(f"❌ Streamlit应用状态异常: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Streamlit应用未运行")
        print("💡 提示: 运行 'python run_app.py' 启动应用")
        return False
    except Exception as e:
        print(f"❌ Streamlit检查出错: {e}")
        return False

def check_wms_service():
    """检查WMS服务"""
    print("\n4️⃣ 检查WMS服务...")
    
    try:
        wms_url = "http://localhost:8080/geoserver/evacuation/wms?service=WMS&version=1.1.0&request=GetCapabilities"
        response = requests.get(wms_url, timeout=10)
        
        if response.status_code == 200 and 'WMS_Capabilities' in response.text:
            print("✅ WMS服务正常")
            print("🗺️  WMS能力文档可访问")
            return True
        else:
            print("❌ WMS服务异常")
            return False
    except Exception as e:
        print(f"❌ WMS服务检查出错: {e}")
        return False

def main():
    """主验证函数"""
    print("=" * 60)
    print("🔍 疏散中心选址决策支持系统 - 连接验证")
    print("=" * 60)
    
    checks = [
        check_database(),
        check_geoserver(),
        check_streamlit(),
        check_wms_service()
    ]
    
    passed = sum(checks)
    total = len(checks)
    
    print("\n" + "=" * 60)
    print("📋 验证结果汇总")
    print("=" * 60)
    print(f"通过检查: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有组件连接正常！系统可以正常使用")
        print("\n🚀 快速开始:")
        print("1. 访问应用: http://localhost:8501")
        print("2. 访问GeoServer: http://localhost:8080/geoserver/web")
        print("3. 查看数据库: 使用pgAdmin或其他PostgreSQL客户端")
    else:
        print("⚠️  部分组件连接异常，请检查相关配置")
        
        if not checks[0]:
            print("- 检查PostgreSQL是否运行，数据库配置是否正确")
        if not checks[1]:
            print("- 检查GeoServer是否运行，用户名密码是否正确")
        if not checks[2]:
            print("- 运行 'python run_app.py' 启动Streamlit应用")
        if not checks[3]:
            print("- 确保evacuation工作空间和PostGIS数据存储已创建")

if __name__ == "__main__":
    main()
