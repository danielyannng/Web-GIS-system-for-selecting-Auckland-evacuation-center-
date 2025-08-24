#!/bin/bash
# 疏散中心选址系统 - 快速打包脚本

echo "🎁 开始打包疏散中心选址决策支持系统..."

# 创建打包目录
PACKAGE_NAME="evacuation_center_system_$(date +%Y%m%d_%H%M%S)"
PACKAGE_DIR="package/$PACKAGE_NAME"

mkdir -p "$PACKAGE_DIR"

echo "📁 复制项目文件..."

# 复制主要项目文件
cp -r src/ "$PACKAGE_DIR/" 2>/dev/null || echo "  ⚠️  src目录不存在"
cp -r data/ "$PACKAGE_DIR/" 2>/dev/null || echo "  ⚠️  data目录不存在"
cp -r scripts/ "$PACKAGE_DIR/" 2>/dev/null || echo "  ⚠️  scripts目录不存在"
cp -r docs/ "$PACKAGE_DIR/" 2>/dev/null || echo "  ⚠️  docs目录不存在"

# 复制配置文件
cp *.py "$PACKAGE_DIR/" 2>/dev/null
cp *.txt "$PACKAGE_DIR/" 2>/dev/null
cp *.md "$PACKAGE_DIR/" 2>/dev/null
cp *.sh "$PACKAGE_DIR/" 2>/dev/null
cp *.yml "$PACKAGE_DIR/" 2>/dev/null
cp *.yaml "$PACKAGE_DIR/" 2>/dev/null

echo "🐳 创建Docker配置..."

# 创建完整的docker-compose.yml
cat > "$PACKAGE_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

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
EOF

# 创建Dockerfile
cat > "$PACKAGE_DIR/Dockerfile" << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gcc \
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
EOF

# 创建部署脚本
cat > "$PACKAGE_DIR/deploy.sh" << 'EOF'
#!/bin/bash
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
sleep 10
docker-compose exec streamlit python scripts/import_data_to_postgres.py || echo "⚠️ 数据导入可能失败，请手动执行"
docker-compose exec streamlit python scripts/import_qgis_to_postgres.py || echo "⚠️ QGIS数据导入可能失败，请手动执行"
docker-compose exec streamlit python scripts/publish_to_geoserver.py || echo "⚠️ GeoServer发布可能失败，请手动执行"

echo "✅ 部署完成！"
echo ""
echo "🌐 访问地址:"
echo "  - 主应用: http://localhost:8501"
echo "  - GeoServer: http://localhost:8080/geoserver"
echo "  - GeoServer管理: http://localhost:8080/geoserver/web (admin/geoserver)"
echo ""
echo "🛑 停止服务: docker-compose down"
echo "📊 查看日志: docker-compose logs -f [service_name]"
EOF

chmod +x "$PACKAGE_DIR/deploy.sh"

# 创建数据库初始化目录和脚本
mkdir -p "$PACKAGE_DIR/init-scripts"
cat > "$PACKAGE_DIR/init-scripts/01-init-postgis.sql" << 'EOF'
-- 初始化PostGIS扩展
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 设置搜索路径
ALTER DATABASE evacuation SET search_path TO public, postgis;
EOF

# 创建部署文档
cat > "$PACKAGE_DIR/README_DEPLOYMENT.md" << EOF
# 疏散中心选址决策支持系统 - 部署包

**Package**: $PACKAGE_NAME
**Generated**: $(date '+%Y-%m-%d %H:%M:%S')

## 🚀 快速部署

### 1. 环境要求
- Docker 20.0+
- Docker Compose 1.28+
- 至少4GB可用内存
- 端口 5432, 8080, 8501 未被占用

### 2. 一键部署
\`\`\`bash
chmod +x deploy.sh
./deploy.sh
\`\`\`

### 3. 访问系统
- **主应用**: http://localhost:8501
- **GeoServer**: http://localhost:8080/geoserver
- **GeoServer管理**: http://localhost:8080/geoserver/web (admin/geoserver)

## 🛠️ 管理命令

\`\`\`bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
\`\`\`

## 🗄️ 数据库连接
- 主机: localhost:5432
- 数据库: evacuation
- 用户: postgres
- 密码: postgres

## 📞 故障排除

如遇问题，请检查：
1. Docker服务是否运行
2. 端口是否被占用
3. 系统资源是否充足
4. 查看容器日志：docker-compose logs

EOF

echo "📦 创建压缩包..."
cd package
zip -r "$PACKAGE_NAME.zip" "$PACKAGE_NAME" > /dev/null 2>&1

FILE_SIZE=$(du -sh "$PACKAGE_NAME.zip" | cut -f1)

echo ""
echo "🎉 打包完成！"
echo "📦 压缩包: package/$PACKAGE_NAME.zip ($FILE_SIZE)"
echo "📁 目录: package/$PACKAGE_NAME"
echo ""
echo "🚀 部署说明:"
echo "1. 解压到目标服务器: unzip $PACKAGE_NAME.zip"
echo "2. 进入目录: cd $PACKAGE_NAME"
echo "3. 执行部署: ./deploy.sh"
echo "4. 访问系统: http://localhost:8501"
