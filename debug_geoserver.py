#!/usr/bin/env python3
"""
GeoServer连接调试脚本
GeoServer Connection Debug Script
"""

import requests
import json

def test_geoserver_basic():
    """测试基本GeoServer连接"""
    print("🔧 GeoServer连接调试")
    print("=" * 50)
    
    base_url = "http://localhost:8080/geoserver"
    
    # 测试基本连接
    print("1. 测试基本连接...")
    try:
        response = requests.get(f"{base_url}/web/", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GeoServer Web界面可访问")
        else:
            print(f"   ⚠️  响应状态: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False
    
    # 测试REST API认证
    print("\n2. 测试REST API认证...")
    
    credentials = [
        ('admin', 'admin'),
        ('admin', 'geoserver'),
        ('admin', 'password'),
        ('geoserver', 'geoserver')
    ]
    
    for username, password in credentials:
        print(f"   尝试用户: {username}/{password}")
        try:
            response = requests.get(
                f"{base_url}/rest/about/version.json",
                auth=(username, password),
                timeout=5
            )
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 认证成功!")
                version_info = response.json()
                print(f"   GeoServer版本: {version_info.get('about', {}).get('resource', [{}])[0].get('Version', 'Unknown')}")
                return username, password
            elif response.status_code == 401:
                print(f"   ❌ 认证失败")
            else:
                print(f"   ⚠️  其他错误: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
    
    print("\n❌ 所有认证尝试都失败了")
    return None

def test_workspace_creation(username, password):
    """测试工作空间创建"""
    print("\n3. 测试工作空间操作...")
    
    base_url = "http://localhost:8080/geoserver"
    auth = (username, password)
    
    # 获取现有工作空间
    try:
        response = requests.get(
            f"{base_url}/rest/workspaces.json",
            auth=auth,
            timeout=5
        )
        
        if response.status_code == 200:
            workspaces = response.json()
            workspace_names = [ws['name'] for ws in workspaces.get('workspaces', {}).get('workspace', [])]
            print(f"   现有工作空间: {', '.join(workspace_names)}")
            
            if 'evacuation' in workspace_names:
                print("   ✅ evacuation工作空间已存在")
                return True
            else:
                print("   ⚠️  evacuation工作空间不存在，尝试创建...")
                return create_evacuation_workspace(base_url, auth)
        else:
            print(f"   ❌ 获取工作空间失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 工作空间操作失败: {e}")
        return False

def create_evacuation_workspace(base_url, auth):
    """创建evacuation工作空间"""
    try:
        workspace_data = {
            "workspace": {
                "name": "evacuation"
            }
        }
        
        response = requests.post(
            f"{base_url}/rest/workspaces",
            json=workspace_data,
            auth=auth,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            print("   ✅ evacuation工作空间创建成功")
            return True
        else:
            print(f"   ❌ 工作空间创建失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 工作空间创建失败: {e}")
        return False

def main():
    """主函数"""
    result = test_geoserver_basic()
    
    if result:
        username, password = result
        print(f"\n🎉 找到有效认证: {username}/{password}")
        
        # 测试工作空间
        if test_workspace_creation(username, password):
            print("\n✅ GeoServer配置正常，可以继续使用")
            print(f"\n📝 请在应用中使用以下认证信息:")
            print(f"   用户名: {username}")
            print(f"   密码: {password}")
            print(f"   URL: http://localhost:8080/geoserver")
        else:
            print("\n⚠️  工作空间配置有问题")
    else:
        print("\n❌ 无法连接到GeoServer")
        print("\n💡 可能的解决方案:")
        print("1. 确保GeoServer正在运行")
        print("2. 检查GeoServer是否正确安装")
        print("3. 重新启动GeoServer服务")
        print("4. 检查防火墙设置")

if __name__ == "__main__":
    main()
