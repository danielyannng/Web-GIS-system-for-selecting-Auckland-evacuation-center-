#!/bin/bash
# Docker容器和数据导出脚本

echo "🐳 Docker容器和数据导出工具"
echo "================================"

# 创建导出目录
EXPORT_DIR="docker_export_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EXPORT_DIR"

echo "📁 导出目录: $EXPORT_DIR"

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请启动Docker后重试"
    exit 1
fi

echo ""
echo "🔍 查找相关容器..."

# 查找PostgreSQL容器
POSTGRES_CONTAINERS=$(docker ps -a --filter "ancestor=postgres" --format "{{.Names}}" 2>/dev/null)
if [ ! -z "$POSTGRES_CONTAINERS" ]; then
    echo "📊 找到PostgreSQL容器:"
    echo "$POSTGRES_CONTAINERS" | while read container; do
        echo "  - $container"
    done
else
    echo "⚠️  未找到PostgreSQL容器"
fi

# 查找GeoServer容器
GEOSERVER_CONTAINERS=$(docker ps -a --filter "name=geoserver" --format "{{.Names}}" 2>/dev/null)
if [ ! -z "$GEOSERVER_CONTAINERS" ]; then
    echo "🗺️  找到GeoServer容器:"
    echo "$GEOSERVER_CONTAINERS" | while read container; do
        echo "  - $container"
    done
else
    echo "⚠️  未找到GeoServer容器"
fi

echo ""
echo "📦 导出Docker镜像..."

# 导出PostgreSQL镜像
if [ ! -z "$POSTGRES_CONTAINERS" ]; then
    echo "$POSTGRES_CONTAINERS" | while read container; do
        image=$(docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null)
        if [ ! -z "$image" ]; then
            echo "  导出PostgreSQL镜像: $image"
            docker save -o "$EXPORT_DIR/postgres_${container}.tar" "$image"
            if [ $? -eq 0 ]; then
                echo "    ✅ 导出成功: postgres_${container}.tar"
            else
                echo "    ❌ 导出失败"
            fi
        fi
    done
fi

# 导出GeoServer镜像
if [ ! -z "$GEOSERVER_CONTAINERS" ]; then
    echo "$GEOSERVER_CONTAINERS" | while read container; do
        image=$(docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null)
        if [ ! -z "$image" ]; then
            echo "  导出GeoServer镜像: $image"
            docker save -o "$EXPORT_DIR/geoserver_${container}.tar" "$image"
            if [ $? -eq 0 ]; then
                echo "    ✅ 导出成功: geoserver_${container}.tar"
            else
                echo "    ❌ 导出失败"
            fi
        fi
    done
fi

echo ""
echo "💾 导出数据卷..."

# 查找相关数据卷
VOLUMES=$(docker volume ls --format "{{.Name}}" | grep -E "(postgres|geoserver|evacuation)" 2>/dev/null)

if [ ! -z "$VOLUMES" ]; then
    mkdir -p "$EXPORT_DIR/volumes"
    echo "$VOLUMES" | while read volume; do
        echo "  备份数据卷: $volume"
        docker run --rm \
            -v "$volume:/data" \
            -v "$(pwd)/$EXPORT_DIR/volumes:/backup" \
            alpine \
            tar czf "/backup/${volume}_backup.tar.gz" -C /data .
        
        if [ $? -eq 0 ]; then
            echo "    ✅ 备份成功: ${volume}_backup.tar.gz"
        else
            echo "    ❌ 备份失败"
        fi
    done
else
    echo "⚠️  未找到相关数据卷"
fi

echo ""
echo "🗄️ 导出数据库数据..."

# 尝试导出PostgreSQL数据
if [ ! -z "$POSTGRES_CONTAINERS" ]; then
    mkdir -p "$EXPORT_DIR/database"
    echo "$POSTGRES_CONTAINERS" | while read container; do
        echo "  导出数据库: $container"
        
        # 检查容器是否运行
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            # 导出evacuation数据库
            docker exec "$container" pg_dump -U postgres evacuation > "$EXPORT_DIR/database/${container}_evacuation.sql" 2>/dev/null
            if [ $? -eq 0 ] && [ -s "$EXPORT_DIR/database/${container}_evacuation.sql" ]; then
                echo "    ✅ 导出evacuation数据库成功"
            else
                echo "    ⚠️  evacuation数据库导出失败或为空"
                rm -f "$EXPORT_DIR/database/${container}_evacuation.sql"
            fi
            
            # 导出所有数据库
            docker exec "$container" pg_dumpall -U postgres > "$EXPORT_DIR/database/${container}_all.sql" 2>/dev/null
            if [ $? -eq 0 ] && [ -s "$EXPORT_DIR/database/${container}_all.sql" ]; then
                echo "    ✅ 导出所有数据库成功"
            else
                echo "    ⚠️  所有数据库导出失败"
                rm -f "$EXPORT_DIR/database/${container}_all.sql"
            fi
        else
            echo "    ⚠️  容器未运行，跳过数据库导出"
        fi
    done
fi

echo ""
echo "📝 创建恢复脚本..."

# 创建恢复脚本
cat > "$EXPORT_DIR/restore.sh" << 'EOF'
#!/bin/bash
# Docker容器和数据恢复脚本

echo "🔄 Docker容器和数据恢复工具"
echo "=========================="

# 加载镜像
echo "📦 加载Docker镜像..."
for image in *.tar; do
    if [ -f "$image" ]; then
        echo "  加载: $image"
        docker load -i "$image"
    fi
done

# 恢复数据卷
if [ -d "volumes" ]; then
    echo ""
    echo "💾 恢复数据卷..."
    for backup in volumes/*_backup.tar.gz; do
        if [ -f "$backup" ]; then
            volume_name=$(basename "$backup" _backup.tar.gz)
            echo "  恢复数据卷: $volume_name"
            
            # 创建数据卷
            docker volume create "$volume_name"
            
            # 恢复数据
            docker run --rm \
                -v "$volume_name:/data" \
                -v "$(pwd)/volumes:/backup" \
                alpine \
                tar xzf "/backup/$(basename "$backup")" -C /data
            
            if [ $? -eq 0 ]; then
                echo "    ✅ 恢复成功"
            else
                echo "    ❌ 恢复失败"
            fi
        fi
    done
fi

echo ""
echo "✅ 恢复完成！"
echo ""
echo "💡 提示："
echo "1. 恢复后请检查容器配置"
echo "2. 可能需要重新创建容器来使用恢复的数据卷"
echo "3. 数据库SQL文件位于database/目录，可手动导入"
EOF

chmod +x "$EXPORT_DIR/restore.sh"

# 创建说明文档
cat > "$EXPORT_DIR/README.md" << EOF
# Docker导出包说明

**导出时间**: $(date '+%Y-%m-%d %H:%M:%S')

## 📦 包含内容

- **Docker镜像**: *.tar 文件
- **数据卷备份**: volumes/ 目录
- **数据库SQL**: database/ 目录
- **恢复脚本**: restore.sh

## 🔄 恢复方法

### 1. 自动恢复
\`\`\`bash
chmod +x restore.sh
./restore.sh
\`\`\`

### 2. 手动恢复

#### 加载镜像
\`\`\`bash
docker load -i postgres_*.tar
docker load -i geoserver_*.tar
\`\`\`

#### 恢复数据卷
\`\`\`bash
# 创建数据卷
docker volume create volume_name

# 恢复数据
docker run --rm -v volume_name:/data -v \$(pwd)/volumes:/backup alpine tar xzf /backup/volume_name_backup.tar.gz -C /data
\`\`\`

#### 恢复数据库
\`\`\`bash
# 启动PostgreSQL容器
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres postgres

# 导入数据
docker exec -i postgres psql -U postgres < database/container_name_all.sql
\`\`\`

## 📝 注意事项

1. 恢复前请确保Docker已安装并运行
2. 恢复的数据卷需要重新关联到容器
3. 数据库密码等配置可能需要调整
4. 建议在测试环境先验证恢复效果
EOF

# 创建压缩包
echo ""
echo "📦 创建压缩包..."
tar czf "${EXPORT_DIR}.tar.gz" "$EXPORT_DIR"

if [ $? -eq 0 ]; then
    ARCHIVE_SIZE=$(du -sh "${EXPORT_DIR}.tar.gz" | cut -f1)
    echo "✅ 压缩包创建成功: ${EXPORT_DIR}.tar.gz ($ARCHIVE_SIZE)"
else
    echo "❌ 压缩包创建失败"
fi

echo ""
echo "🎉 导出完成！"
echo ""
echo "📁 导出目录: $EXPORT_DIR"
echo "📦 压缩包: ${EXPORT_DIR}.tar.gz"
echo ""
echo "💡 使用说明："
echo "1. 将压缩包传输到目标服务器"
echo "2. 解压: tar xzf ${EXPORT_DIR}.tar.gz"
echo "3. 进入目录: cd $EXPORT_DIR"
echo "4. 执行恢复: ./restore.sh"
