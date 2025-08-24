#!/usr/bin/env python3
"""
疏散中心选址决策支持系统 - 项目打包脚本
Evacuation Center Site Selection System - Project Packaging Script
"""

import os
import sys
import shutil
import zipfile
import subprocess
import json
from datetime import datetime

def create_packaging_structure():
    """创建打包目录结构"""
    package_name = f"evacuation_center_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    package_dir = os.path.join(os.getcwd(), "package", package_name)
    
    # 创建打包目录
    os.makedirs(package_dir, exist_ok=True)
    
    return package_dir, package_name

def copy_project_files(package_dir):
    """复制项目文件"""
    print("📁 复制项目文件...")
    
    # 要包含的文件和目录
    include_patterns = [
        "*.py",
        "*.md", 
        "*.txt",
        "*.sh",
        "*.yml",
        "*.yaml",
        "src/",
        "data/",
        "scripts/",
        "docs/",
        "requirements.txt",
        "config.py"
    ]
    
    # 要排除的文件和目录
    exclude_patterns = [
        "__pycache__/",
        "*.pyc",
        ".git/",
        ".DS_Store",
        "*.log",
        "package/"
    ]
    
    # 获取当前目录的所有文件
    current_dir = os.getcwd()
    
    for root, dirs, files in os.walk(current_dir):
        # 排除特定目录
        dirs[:] = [d for d in dirs if not any(pattern.rstrip('/') in d for pattern in exclude_patterns)]
        
        for file in files:
            # 检查是否应该包含此文件
            if any(pattern.rstrip('/') in file or file.endswith(pattern.replace('*', '')) for pattern in exclude_patterns):
                continue
                
            source_path = os.path.join(root, file)
            relative_path = os.path.relpath(source_path, current_dir)
            
            # 跳过package目录本身
            if relative_path.startswith('package/'):
                continue
                
            dest_path = os.path.join(package_dir, relative_path)
            
            # 创建目标目录
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # 复制文件
            try:
                shutil.copy2(source_path, dest_path)
                print(f"  ✅ {relative_path}")
            except Exception as e:
                print(f"  ❌ 复制失败 {relative_path}: {e}")

def export_docker_containers(package_dir):
    """导出Docker容器"""
    print("\n🐳 导出Docker容器...")
    
    docker_dir = os.path.join(package_dir, "docker_images")
    os.makedirs(docker_dir, exist_ok=True)
    
    # 检查Docker是否运行
    try:
        subprocess.run(["docker", "version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("  ❌ Docker未运行，跳过容器导出")
        return
    
    # 查找相关容器
    containers = []
    try:
        # 查找PostgreSQL容器
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "ancestor=postgres", "--format", "{{.Names}}\t{{.Image}}"],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                name, image = line.split('\t')
                containers.append(('postgres', name, image))
        
        # 查找GeoServer容器
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=geoserver", "--format", "{{.Names}}\t{{.Image}}"],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                name, image = line.split('\t')
                containers.append(('geoserver', name, image))
                
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 查找容器失败: {e}")
        return
    
    # 导出容器镜像
    for service_type, container_name, image_name in containers:
        print(f"  📦 导出 {service_type} 容器: {container_name}")
        output_file = os.path.join(docker_dir, f"{service_type}_{container_name}.tar")
        
        try:
            subprocess.run(
                ["docker", "save", "-o", output_file, image_name],
                check=True
            )
            print(f"    ✅ 已保存到: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"    ❌ 导出失败: {e}")

def export_docker_volumes(package_dir):
    """导出Docker数据卷"""
    print("\n💾 导出Docker数据卷...")
    
    volumes_dir = os.path.join(package_dir, "docker_volumes")
    os.makedirs(volumes_dir, exist_ok=True)
    
    try:
        # 获取所有卷
        result = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        
        volumes = [v.strip() for v in result.stdout.strip().split('\n') if v.strip()]
        
        for volume in volumes:
            if any(keyword in volume.lower() for keyword in ['postgres', 'geoserver', 'evacuation']):
                print(f"  📂 备份卷: {volume}")
                backup_file = os.path.join(volumes_dir, f"{volume}_backup.tar")
                
                try:
                    # 使用临时容器备份卷
                    subprocess.run([
                        "docker", "run", "--rm", 
                        "-v", f"{volume}:/data",
                        "-v", f"{volumes_dir}:/backup",
                        "alpine",
                        "tar", "czf", f"/backup/{volume}_backup.tar", "-C", "/data", "."
                    ], check=True)
                    print(f"    ✅ 已备份到: {backup_file}")
                except subprocess.CalledProcessError as e:
                    print(f"    ❌ 备份失败: {e}")
                    
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 获取卷列表失败: {e}")

def create_deployment_scripts(package_dir):
    """创建部署脚本"""
    print("\n📜 创建部署脚本...")
    
    # 创建完整的docker-compose文件
    docker_compose_content = """version: '3.8'

services:
  postgres:
    image: postgres:13
    container_name: evacuation-postgres
    environment:
      POSTGRES_DB: evacuation
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_INITDB_ARGS: "--encoding=UTF8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    networks:
      - evacuation_network
    restart: unless-stopped

  geoserver:
    image: kartoza/geoserver:2.21.0
    container_name: evacuation-geoserver
    environment:
      GEOSERVER_ADMIN_PASSWORD: geoserver
      GEOSERVER_ADMIN_USER: admin
      INITIAL_MEMORY: 2G
      MAXIMUM_MEMORY: 4G
      STABLE_EXTENSIONS: wps-extension,csw-extension
      COMMUNITY_EXTENSIONS: importer-extension
    ports:
      - "8080:8080"
    volumes:
      - geoserver_data:/opt/geoserver/data_dir
    networks:
      - evacuation_network
    depends_on:
      - postgres
    restart: unless-stopped

  streamlit:
    build: .
    container_name: evacuation-streamlit
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./src:/app/src
    networks:
      - evacuation_network
    depends_on:
      - postgres
      - geoserver
    environment:
      - POSTGRES_HOST=postgres
      - GEOSERVER_URL=http://geoserver:8080/geoserver
    restart: unless-stopped

volumes:
  postgres_data:
  geoserver_data:

networks:
  evacuation_network:
    driver: bridge
"""
    
    # 创建Dockerfile
    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gdal-bin \\
    libgdal-dev \\
    libpq-dev \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# 复制requirements并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "app_simple.py", "--server.port=8501", "--server.address=0.0.0.0"]
"""
    
    # 创建部署脚本
    deploy_script_content = """#!/bin/bash
# 疏散中心选址系统部署脚本

echo "🚀 开始部署疏散中心选址决策支持系统..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 停止已存在的容器
echo "🛑 停止现有容器..."
docker-compose down

# 加载Docker镜像（如果存在）
if [ -d "docker_images" ]; then
    echo "📦 加载Docker镜像..."
    for image in docker_images/*.tar; do
        if [ -f "$image" ]; then
            echo "  加载: $image"
            docker load -i "$image"
        fi
    done
fi

# 恢复数据卷（如果存在）
if [ -d "docker_volumes" ]; then
    echo "💾 恢复数据卷..."
    for backup in docker_volumes/*_backup.tar; do
        if [ -f "$backup" ]; then
            volume_name=$(basename "$backup" _backup.tar)
            echo "  恢复卷: $volume_name"
            docker volume create "$volume_name"
            docker run --rm -v "$volume_name:/data" -v "$(pwd)/docker_volumes:/backup" alpine tar xzf "/backup/$(basename "$backup")" -C /data
        fi
    done
fi

# 构建和启动服务
echo "🏗️ 构建和启动服务..."
docker-compose up --build -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 导入数据
echo "📊 导入数据..."
docker-compose exec streamlit python scripts/import_data_to_postgres.py
docker-compose exec streamlit python scripts/import_qgis_to_postgres.py
docker-compose exec streamlit python scripts/publish_to_geoserver.py

echo "✅ 部署完成！"
echo ""
echo "🌐 访问地址:"
echo "  - 主应用: http://localhost:8501"
echo "  - GeoServer: http://localhost:8080/geoserver"
echo "  - GeoServer管理: http://localhost:8080/geoserver/web (admin/geoserver)"
echo ""
echo "🛑 停止服务: docker-compose down"
echo "📊 查看日志: docker-compose logs -f [service_name]"
"""
    
    # 创建PostGIS初始化脚本
    init_script_content = """-- 初始化PostGIS扩展
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 创建应用用户
-- CREATE USER evacuation_user WITH PASSWORD 'evacuation_pass';
-- GRANT ALL PRIVILEGES ON DATABASE evacuation TO evacuation_user;

-- 设置搜索路径
ALTER DATABASE evacuation SET search_path TO public, postgis;
"""
    
    # 写入文件
    with open(os.path.join(package_dir, "docker-compose.yml"), "w", encoding="utf-8") as f:
        f.write(docker_compose_content)
    
    with open(os.path.join(package_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile_content)
    
    deploy_script_path = os.path.join(package_dir, "deploy.sh")
    with open(deploy_script_path, "w", encoding="utf-8") as f:
        f.write(deploy_script_content)
    os.chmod(deploy_script_path, 0o755)
    
    # 创建初始化脚本目录
    init_dir = os.path.join(package_dir, "init-scripts")
    os.makedirs(init_dir, exist_ok=True)
    
    with open(os.path.join(init_dir, "01-init-postgis.sql"), "w", encoding="utf-8") as f:
        f.write(init_script_content)
    
    print("  ✅ docker-compose.yml")
    print("  ✅ Dockerfile")
    print("  ✅ deploy.sh")
    print("  ✅ init-scripts/01-init-postgis.sql")

def create_documentation(package_dir, package_name):
    """创建部署文档"""
    print("\n📚 创建部署文档...")
    
    readme_content = f"""# 疏散中心选址决策支持系统 - 部署包

**Package**: {package_name}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📦 包内容

```
{package_name}/
├── app_simple.py              # 主应用程序
├── requirements.txt           # Python依赖
├── docker-compose.yml         # Docker编排文件
├── Dockerfile                 # 应用容器构建文件
├── deploy.sh                  # 一键部署脚本
├── src/                       # 源代码目录
├── data/                      # 数据文件
├── scripts/                   # 管理脚本
├── docs/                      # 项目文档
├── init-scripts/              # 数据库初始化脚本
├── docker_images/             # Docker镜像文件 (如果导出)
├── docker_volumes/            # 数据卷备份 (如果导出)
└── README_DEPLOYMENT.md       # 本文件
```

## 🚀 快速部署

### 1. 环境要求
- Docker 20.0+
- Docker Compose 1.28+
- 至少4GB可用内存
- 端口 5432, 8080, 8501 未被占用

### 2. 一键部署
```bash
chmod +x deploy.sh
./deploy.sh
```

### 3. 手动部署
```bash
# 启动所有服务
docker-compose up -d

# 等待服务启动 (约2-3分钟)
docker-compose ps

# 导入数据
docker-compose exec streamlit python scripts/import_data_to_postgres.py
docker-compose exec streamlit python scripts/import_qgis_to_postgres.py
docker-compose exec streamlit python scripts/publish_to_geoserver.py
```

## 🌐 访问系统

- **主应用**: http://localhost:8501
- **GeoServer**: http://localhost:8080/geoserver
- **GeoServer管理**: http://localhost:8080/geoserver/web
  - 用户名: admin
  - 密码: geoserver

## 🛠️ 管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]

# 重启特定服务
docker-compose restart [service_name]

# 停止所有服务
docker-compose down

# 完全清理 (包括数据)
docker-compose down -v
docker system prune -f
```

## 🗄️ 数据库连接

- **主机**: localhost
- **端口**: 5432
- **数据库**: evacuation
- **用户名**: postgres
- **密码**: postgres

## 📊 数据说明

系统包含以下数据集：
- 奥克兰设施数据 (医院、学校等)
- 人口分布数据
- 道路网络数据
- 风险区域数据
- 行政边界数据

## 🐛 故障排除

### 服务无法启动
```bash
# 检查端口占用
netstat -an | grep :8501
netstat -an | grep :8080
netstat -an | grep :5432

# 查看详细错误
docker-compose logs
```

### 数据导入失败
```bash
# 检查PostgreSQL连接
docker-compose exec streamlit python -c "import psycopg2; print('OK')"

# 手动重新导入
docker-compose exec streamlit python scripts/verify_database.py
```

### GeoServer无法访问
```bash
# 重启GeoServer
docker-compose restart geoserver

# 检查GeoServer日志
docker-compose logs geoserver
```

## 📝 系统配置

### 修改端口
编辑 `docker-compose.yml` 文件中的端口映射：
```yaml
ports:
  - "YOUR_PORT:8501"  # 主应用
  - "YOUR_PORT:8080"  # GeoServer
  - "YOUR_PORT:5432"  # PostgreSQL
```

### 修改数据库密码
编辑 `docker-compose.yml` 文件中的环境变量：
```yaml
environment:
  POSTGRES_PASSWORD: your_new_password
```

## 🔒 安全注意事项

1. **生产环境部署**:
   - 修改默认密码
   - 配置防火墙规则
   - 启用HTTPS
   - 限制数据库访问

2. **数据备份**:
   ```bash
   # 备份数据库
   docker-compose exec postgres pg_dump -U postgres evacuation > backup.sql
   
   # 备份GeoServer配置
   docker cp evacuation-geoserver:/opt/geoserver/data_dir ./geoserver_backup
   ```

## 📞 技术支持

如有问题，请检查：
1. Docker服务是否正常运行
2. 系统资源是否充足
3. 网络连接是否正常
4. 日志文件中的错误信息

---

**版本**: 1.0.0
**更新**: {datetime.now().strftime('%Y-%m-%d')}
"""
    
    with open(os.path.join(package_dir, "README_DEPLOYMENT.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("  ✅ README_DEPLOYMENT.md")

def create_package_archive(package_dir, package_name):
    """创建压缩包"""
    print(f"\n📦 创建压缩包: {package_name}.zip")
    
    zip_path = os.path.join(os.path.dirname(package_dir), f"{package_name}.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(package_dir))
                zipf.write(file_path, arcname)
                
    file_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
    print(f"  ✅ 压缩包已创建: {zip_path}")
    print(f"  📏 文件大小: {file_size:.1f} MB")
    
    return zip_path

def main():
    """主函数"""
    print("🎁 疏散中心选址决策支持系统 - 项目打包工具")
    print("=" * 60)
    
    try:
        # 创建打包结构
        package_dir, package_name = create_packaging_structure()
        print(f"📁 创建打包目录: {package_dir}")
        
        # 复制项目文件
        copy_project_files(package_dir)
        
        # 导出Docker容器 (可选)
        export_docker_containers(package_dir)
        
        # 导出Docker数据卷 (可选)
        export_docker_volumes(package_dir)
        
        # 创建部署脚本
        create_deployment_scripts(package_dir)
        
        # 创建文档
        create_documentation(package_dir, package_name)
        
        # 创建压缩包
        zip_path = create_package_archive(package_dir, package_name)
        
        print("\n" + "=" * 60)
        print("🎉 打包完成！")
        print(f"📦 压缩包位置: {zip_path}")
        print(f"📁 解压目录: {package_dir}")
        print("\n🚀 部署说明:")
        print("1. 解压压缩包到目标服务器")
        print("2. 进入解压目录")
        print("3. 运行: chmod +x deploy.sh && ./deploy.sh")
        print("4. 访问: http://localhost:8501")
        
    except Exception as e:
        print(f"\n❌ 打包失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
